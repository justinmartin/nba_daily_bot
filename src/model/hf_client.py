
import sys
import os
import logging
import re
from src.config import Config

logger = logging.getLogger(__name__)
cfg = Config()


def _build_payload(model_id: str, prompt: str, max_tokens: int = None):
    return {
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "model": model_id,
        "max_tokens": max_tokens or cfg.MAX_TOKENS,
        "temperature": 0.8,
        "top_p": 0.95,
    }


def _post_chat_completion(requests_module, api_url: str, headers: dict, payload: dict):
    response = requests_module.post(api_url, headers=headers, json=payload, timeout=60)
    if not response.ok:
        body_preview = response.text[:1000]
        try:
            error_json = response.json()
        except Exception:
            error_json = {}

        error_message = error_json.get("error", {}).get("message", "")
        error_code = error_json.get("error", {}).get("code", "")
        raise requests_module.HTTPError(
            f"HF API {response.status_code} ({error_code}): {error_message or body_preview}",
            response=response,
        )
    return response.json()


def _extract_safe_max_tokens(error_message: str):
    # HF returns messages like:
    # "maximum context length is 4096 tokens and your request has 3977 input tokens"
    # We keep a small headroom to avoid edge rounding failures on retry.
    match = re.search(r"maximum context length is\s*(\d+)\s*tokens.*?has\s*(\d+)\s*input tokens", error_message, re.IGNORECASE)
    if not match:
        return None

    context_limit = int(match.group(1))
    input_tokens = int(match.group(2))
    safe_budget = context_limit - input_tokens - 16
    if safe_budget <= 0:
        return None
    return safe_budget


def _extract_message_and_finish_reason(result: dict):
    choices = result.get("choices", []) if isinstance(result, dict) else []
    if not choices:
        return "", ""
    first = choices[0] or {}
    message = first.get("message", {}).get("content", "") or ""
    finish_reason = first.get("finish_reason", "") or ""
    return message, finish_reason


def _looks_cut_off(text: str) -> bool:
    if not text:
        return False
    stripped = text.rstrip()
    if len(stripped) < 120:
        return False
    return stripped[-1] not in {".", "!", "?", '"', "'", "…"}


def _continue_prompt(existing_text: str) -> str:
    tail = existing_text[-1400:]
    return (
        "Continue this NBA recap seamlessly from where it stopped. "
        "Do not repeat previous sentences. Do not add title or conclusion. "
        "Start directly with the next sentence and add concrete game details from the provided context only.\n\n"
        f"Text so far:\n{tail}\n\nContinue:"
    )


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

        model_id = cfg.MODEL_ID
        payload = _build_payload(model_id=model_id, prompt=prompt, max_tokens=max_tokens)

        try:
            result = _post_chat_completion(requests, api_url, headers, payload)
        except requests.HTTPError as first_err:
            status_code = getattr(getattr(first_err, "response", None), "status_code", None)
            error_json = {}
            if getattr(first_err, "response", None) is not None:
                try:
                    error_json = first_err.response.json()
                except Exception:
                    error_json = {}

            error_code = error_json.get("error", {}).get("code", "")
            error_message = error_json.get("error", {}).get("message", "")
            should_retry_with_provider = (
                status_code == 400
                and error_code in {"model_not_supported", "model_not_found"}
                and ":" not in model_id
                and bool(cfg.HF_PROVIDER)
            )
            should_retry_with_smaller_tokens = (
                status_code == 400
                and error_code == "bad_request"
                and "max_tokens" in error_message
                and "maximum context length" in error_message
            )

            if should_retry_with_provider:
                fallback_model = f"{model_id}:{cfg.HF_PROVIDER}"
                logger.warning(
                    "⚠️ HF model '%s' failed (%s). Retrying with provider suffix: '%s'",
                    model_id,
                    error_code or status_code,
                    fallback_model,
                )
                payload = _build_payload(model_id=fallback_model, prompt=prompt, max_tokens=max_tokens)
                result = _post_chat_completion(requests, api_url, headers, payload)
            elif should_retry_with_smaller_tokens:
                safe_max_tokens = _extract_safe_max_tokens(error_message)
                if not safe_max_tokens:
                    raise
                logger.warning(
                    "⚠️ Requested max_tokens is too high for prompt size. Retrying with max_tokens=%s",
                    safe_max_tokens,
                )
                payload = _build_payload(model_id=model_id, prompt=prompt, max_tokens=safe_max_tokens)
                result = _post_chat_completion(requests, api_url, headers, payload)
            else:
                raise
        
        message, finish_reason = _extract_message_and_finish_reason(result)
        if message:
            min_chars = max(200, cfg.MIN_SUMMARY_CHARS)
            continuation_limit = max(0, cfg.MAX_SUMMARY_CONTINUATIONS)
            chunk_max_tokens = min(max_tokens or cfg.MAX_TOKENS, 450)

            for idx in range(continuation_limit):
                too_short = len(message.strip()) < min_chars
                cut_off = finish_reason == "length" or _looks_cut_off(message)
                if not too_short and not cut_off:
                    break

                logger.warning(
                    "⚠️ Summary short/cut (len=%s, finish_reason=%s). Requesting continuation %s/%s.",
                    len(message.strip()),
                    finish_reason or "unknown",
                    idx + 1,
                    continuation_limit,
                )

                continuation_prompt = _continue_prompt(message)
                continuation_payload = _build_payload(
                    model_id=model_id,
                    prompt=continuation_prompt,
                    max_tokens=chunk_max_tokens,
                )
                try:
                    continuation_result = _post_chat_completion(requests, api_url, headers, continuation_payload)
                    continuation_text, continuation_finish_reason = _extract_message_and_finish_reason(continuation_result)
                    if not continuation_text:
                        break
                    message = f"{message.rstrip()} {continuation_text.lstrip()}"
                    finish_reason = continuation_finish_reason
                except Exception as cont_err:
                    logger.warning(f"⚠️ Continuation request failed, using current summary: {cont_err}")
                    break

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
