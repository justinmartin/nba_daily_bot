
import sys
import os
import logging
from src.config import Config

logger = logging.getLogger(__name__)
cfg = Config()

def generate_with_hf_openai_api(prompt: str, max_tokens: int = None):
    try:
        import requests
    except ImportError:
        logger.error("❌ requests not installed")
        raise
    
    token = cfg.HF_API_TOKEN
    if not token:
        raise ValueError("❌ HF_API_TOKEN not configured in environment")
    
    try:
        logger.info(f"🤖 Using HF OpenAI API with model {cfg.MODEL_ID}")
        
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
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()  # Lève une exception si erreur HTTP
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            message = result["choices"][0].get("message", {}).get("content", "")
            if message:
                return message
        
        logger.error(f"❌ Unexpected response format: {result}")
        raise ValueError("Invalid response format from HF API")
        
    except Exception as e:
        logger.error(f"❌ HF OpenAI API error: {e}")
        raise

def generate_local(prompt: str, max_tokens: int = None):
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
    except ImportError:
        logger.error("❌ transformers not installed. Install with: pip install transformers torch accelerate")
        raise
    
    try:
        logger.info(f"🤖 Using local model: {cfg.MODEL_ID}")
        
        tokenizer = AutoTokenizer.from_pretrained(cfg.MODEL_ID)
        model = AutoModelForCausalLM.from_pretrained(cfg.MODEL_ID, device_map="cpu")
        
        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        logger.debug(f"Formatted prompt:\n{formatted_prompt[:200]}...")
        
        inputs = tokenizer(formatted_prompt, return_tensors="pt")
        
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens or cfg.MAX_TOKENS,  # Limite de tokens
            do_sample=True,                # Génération stochastique (vs greedy)
            top_p=0.95,                    # Nucleus sampling
            temperature=0.8,               # Créativité
            top_k=40,                      # Limite aux 40 meilleurs tokens
            repetition_penalty=1.1         # Pénalise les répétitions
        )
        
        full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
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
    if not prompt or not prompt.strip():
        raise ValueError("❌ Prompt cannot be empty")
    
    try:
        if cfg.USE_HF_INF_API:
            return generate_with_hf_openai_api(prompt, max_tokens=max_tokens)
        else:
            return generate_local(prompt, max_tokens=max_tokens)
            
    except Exception as e:
        logger.error(f"❌ Text generation failed: {e}")
        raise
