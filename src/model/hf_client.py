"""
Client HuggingFace pour génération de texte IA.

Ce module gère la génération du texte de la newsletter via:
    1. HuggingFace OpenAI-compatible API (recommandé, si USE_HF_INF_API=true)
    2. Modèle local Transformers (si USE_HF_INF_API=false)

API utilisée:
    - HuggingFace Router (https://router.huggingface.co)
    - Endpoint: /v1/chat/completions (format OpenAI)
    - Modèle par défaut: EleutherAI/gpt-neo-125M
    
Configuration requise (.env):
    - HF_API_TOKEN: Token d'authentification HuggingFace
    - MODEL_ID: ID du modèle (ex: "meta-llama/Llama-3.2-3B-Instruct")
    - MAX_TOKENS: Nombre max de tokens générés (défaut: 400)
    - USE_HF_INF_API: true=API cloud, false=modèle local
"""

import sys
import os
import logging
from src.config import Config

logger = logging.getLogger(__name__)
cfg = Config()


def generate_with_hf_openai_api(prompt: str, max_tokens: int = None):
    """
    Génère du texte via l'API OpenAI-compatible de HuggingFace.
    
    Cette méthode est RECOMMANDÉE car:
        - Pas besoin de télécharger le modèle (économie de stockage)
        - Exécution rapide sur serveurs HuggingFace
        - Support des gros modèles (Llama, Mistral, etc.)
    
    Args:
        prompt (str): Texte du prompt à envoyer au modèle
        max_tokens (int, optional): Limite de tokens générés. 
                                   Par défaut: cfg.MAX_TOKENS (400)
    
    Returns:
        str: Texte généré par le modèle
    
    Raises:
        ImportError: Si requests n'est pas installé
        ValueError: Si HF_API_TOKEN manque ou réponse invalide
        Exception: En cas d'erreur réseau ou API
    
    Format de requête:
        POST https://router.huggingface.co/v1/chat/completions
        Headers: Authorization: Bearer <HF_API_TOKEN>
        Body: {
            "messages": [{"role": "user", "content": "<prompt>"}],
            "model": "<MODEL_ID>",
            "max_tokens": 400,
            "temperature": 0.8,
            "top_p": 0.95
        }
    
    Exemple:
        >>> generate_with_hf_openai_api("Write about NBA")
        "The NBA season is heating up with..."
    """
    try:
        import requests
    except ImportError:
        logger.error("❌ requests not installed")
        raise
    
    # === ÉTAPE 1: Vérifier le token API ===
    token = cfg.HF_API_TOKEN
    if not token:
        raise ValueError("❌ HF_API_TOKEN not configured in environment")
    
    try:
        logger.info(f"🤖 Using HF OpenAI API with model {cfg.MODEL_ID}")
        
        # === ÉTAPE 2: Préparer la requête API ===
        api_url = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {token}"}
        
        payload = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "model": cfg.MODEL_ID,
            "max_tokens": max_tokens or cfg.MAX_TOKENS,
            "temperature": 0.8,   # Créativité (0=déterministe, 1=aléatoire)
            "top_p": 0.95,        # Nucleus sampling (diversité des mots)
        }
        
        # === ÉTAPE 3: Envoyer la requête ===
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()  # Lève une exception si erreur HTTP
        result = response.json()
        
        # === ÉTAPE 4: Extraire le texte généré ===
        # Format OpenAI: {"choices": [{"message": {"content": "..."}}]}
        if "choices" in result and len(result["choices"]) > 0:
            message = result["choices"][0].get("message", {}).get("content", "")
            if message:
                return message
        
        # Si format invalide, log et raise
        logger.error(f"❌ Unexpected response format: {result}")
        raise ValueError("Invalid response format from HF API")
        
    except Exception as e:
        logger.error(f"❌ HF OpenAI API error: {e}")
        raise


def generate_local(prompt: str, max_tokens: int = None):
    """
    Génère du texte en utilisant un modèle local (Transformers).
    
    Cette méthode télécharge et exécute le modèle sur la machine locale.
    
    Avantages:
        - Pas besoin d'internet après téléchargement
        - Gratuit (pas de coût API)
        - Contrôle total sur le modèle
    
    Inconvénients:
        - Téléchargement initial long (plusieurs GB)
        - Nécessite beaucoup de RAM (8GB+ recommandé)
        - Exécution lente sur CPU (GPU recommandé pour gros modèles)
    
    Args:
        prompt (str): Texte du prompt à envoyer au modèle
        max_tokens (int, optional): Limite de tokens générés
    
    Returns:
        str: Texte généré par le modèle
    
    Raises:
        ImportError: Si transformers/torch ne sont pas installés
        Exception: En cas d'erreur de chargement ou génération
    
    Optimisations MacBook M4:
        - device_map="cpu" (pas de GPU CUDA, utilise le CPU)
        - do_sample=True (génération non déterministe)
        - top_p=0.95, top_k=40 (qualité de génération)
        - repetition_penalty=1.1 (évite les répétitions)
    
    Exemple:
        >>> generate_local("Write about NBA")
        "The NBA season is heating up with..."
    """
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
    except ImportError:
        logger.error("❌ transformers not installed. Install with: pip install transformers torch accelerate")
        raise
    
    try:
        logger.info(f"🤖 Using local model: {cfg.MODEL_ID}")
        
        # === ÉTAPE 1: Charger le tokenizer et le modèle ===
        # Le tokenizer convertit le texte en tokens (nombres)
        tokenizer = AutoTokenizer.from_pretrained(cfg.MODEL_ID)
        # Le modèle génère le texte (chargé sur CPU car pas de GPU CUDA)
        model = AutoModelForCausalLM.from_pretrained(cfg.MODEL_ID, device_map="cpu")
        
        # === ÉTAPE 2: Formater le prompt avec le template de chat ===
        # Les modèles modernes utilisent des templates spécifiques
        # Ex: "<|user|>\n{prompt}\n<|assistant|>\n"
        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        logger.debug(f"Formatted prompt:\n{formatted_prompt[:200]}...")
        
        # === ÉTAPE 3: Tokeniser le prompt ===
        # Convertit le texte en tenseurs PyTorch
        inputs = tokenizer(formatted_prompt, return_tensors="pt")
        
        # === ÉTAPE 4: Générer le texte ===
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens or cfg.MAX_TOKENS,  # Limite de tokens
            do_sample=True,                # Génération stochastique (vs greedy)
            top_p=0.95,                    # Nucleus sampling
            temperature=0.8,               # Créativité
            top_k=40,                      # Limite aux 40 meilleurs tokens
            repetition_penalty=1.1         # Pénalise les répétitions
        )
        
        # === ÉTAPE 5: Décoder les tokens en texte ===
        full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # === ÉTAPE 6: Extraire uniquement la réponse du modèle ===
        # Le modèle retourne: "<|user|>...<|assistant|>RÉPONSE"
        # On ne garde que la partie après "<|assistant|>"
        if "<|assistant|>" in full_text:
            assistant_response = full_text.split("<|assistant|>")[1].strip()
        else:
            assistant_response = full_text
        
        logger.debug(f"Generated text length: {len(assistant_response)} chars")
        return assistant_response
        
    except Exception as e:
        logger.error(f"❌ Local model generation error: {e}")
        raise


def generate(prompt: str, max_tokens: int = None):
    """
    Génère le contenu de la newsletter en utilisant la méthode configurée.
    
    Fonction principale d'entrée pour la génération de texte.
    Choisit automatiquement entre API cloud ou modèle local selon USE_HF_INF_API.
    
    Args:
        prompt (str): Prompt complet avec instructions et données
        max_tokens (int, optional): Limite de tokens générés
    
    Returns:
        str: Texte généré par le modèle
    
    Raises:
        ValueError: Si le prompt est vide
        Exception: En cas d'erreur de génération
    
    Choix de la méthode:
        - Si USE_HF_INF_API=true → generate_with_hf_openai_api() (recommandé)
        - Si USE_HF_INF_API=false → generate_local() (modèle local)
    
    Exemple:
        >>> prompt = "Write a NBA newsletter about Lakers vs Celtics..."
        >>> text = generate(prompt, max_tokens=500)
        >>> print(text)
        "The Lakers dominated the Celtics tonight..."
    """
    # === VALIDATION DU PROMPT ===
    if not prompt or not prompt.strip():
        raise ValueError("❌ Prompt cannot be empty")
    
    try:
        # === CHOIX DE LA MÉTHODE DE GÉNÉRATION ===
        if cfg.USE_HF_INF_API:
            # Méthode 1: API HuggingFace (cloud, rapide, recommandé)
            return generate_with_hf_openai_api(prompt, max_tokens=max_tokens)
        else:
            # Méthode 2: Modèle local (offline, lent, gratuit)
            return generate_local(prompt, max_tokens=max_tokens)
            
    except Exception as e:
        logger.error(f"❌ Text generation failed: {e}")
        raise
