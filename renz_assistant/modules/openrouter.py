"""
OpenRouter API integration for Renz Assistant
"""
import os
import json
import time
import requests
from typing import Dict, List, Optional, Union, Any

class OpenRouterClient:
    """Client for OpenRouter API integration"""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, api_key: str = "", default_model: str = "openai/gpt-3.5-turbo"):
        """Initialize OpenRouter client"""
        self.api_key = api_key
        self.default_model = default_model
        self.last_response = None
        self.last_request = None
    
    def set_api_key(self, api_key: str) -> None:
        """Set OpenRouter API key"""
        self.api_key = api_key
    
    def set_default_model(self, model: str) -> None:
        """Set default model"""
        self.default_model = model
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models from OpenRouter"""
        if not self.api_key:
            print("⚠️ API key not set")
            return []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://renz-assistant.app",  # Replace with your app's URL
                "X-Title": "Renz Assistant"
            }
            
            response = requests.get(
                f"{self.BASE_URL}/models",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                print(f"⚠️ Error listing models: {response.status_code} - {response.text}")
                return []
        
        except Exception as e:
            print(f"⚠️ Error listing models: {e}")
            return []
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        stream: bool = False,
        stop: Optional[Union[str, List[str]]] = None,
        user: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a chat completion using OpenRouter API
        
        Args:
            messages: List of message objects with role and content
            model: Model to use (defaults to self.default_model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter
            stream: Whether to stream the response
            stop: Stop sequences
            user: User identifier
        
        Returns:
            Response from OpenRouter API
        """
        if not self.api_key:
            print("⚠️ API key not set")
            return {"error": "API key not set"}
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://renz-assistant.app",  # Replace with your app's URL
                "X-Title": "Renz Assistant"
            }
            
            data = {
                "model": model or self.default_model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "stream": stream
            }
            
            if max_tokens:
                data["max_tokens"] = max_tokens
            
            if stop:
                data["stop"] = stop
            
            if user:
                data["user"] = user
            
            # Store request for debugging
            self.last_request = data
            
            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                self.last_response = result
                return result
            else:
                error = {
                    "error": f"API error: {response.status_code}",
                    "details": response.text
                }
                self.last_response = error
                print(f"⚠️ API error: {response.status_code} - {response.text}")
                return error
        
        except Exception as e:
            error = {"error": f"Request failed: {str(e)}"}
            self.last_response = error
            print(f"⚠️ Request failed: {e}")
            return error
    
    def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        stop: Optional[Union[str, List[str]]] = None,
        user: Optional[str] = None,
        callback=None
    ) -> None:
        """
        Stream a chat completion using OpenRouter API
        
        Args:
            messages: List of message objects with role and content
            model: Model to use (defaults to self.default_model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter
            stop: Stop sequences
            user: User identifier
            callback: Function to call with each chunk of the response
        """
        if not self.api_key:
            print("⚠️ API key not set")
            if callback:
                callback({"error": "API key not set"})
            return
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://renz-assistant.app",  # Replace with your app's URL
                "X-Title": "Renz Assistant"
            }
            
            data = {
                "model": model or self.default_model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "stream": True
            }
            
            if max_tokens:
                data["max_tokens"] = max_tokens
            
            if stop:
                data["stop"] = stop
            
            if user:
                data["user"] = user
            
            # Store request for debugging
            self.last_request = data
            
            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=data,
                stream=True
            )
            
            if response.status_code == 200:
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        line_text = line.decode('utf-8')
                        if line_text.startswith('data: '):
                            line_json = line_text[6:]  # Remove 'data: ' prefix
                            if line_json.strip() == '[DONE]':
                                break
                            try:
                                chunk = json.loads(line_json)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    content = chunk['choices'][0].get('delta', {}).get('content', '')
                                    if content:
                                        full_response += content
                                        if callback:
                                            callback({"content": content, "full_response": full_response})
                            except json.JSONDecodeError:
                                pass
                
                # Store the full response for debugging
                self.last_response = {"choices": [{"message": {"content": full_response}}]}
                
                # Final callback with the complete response
                if callback:
                    callback({"content": "", "full_response": full_response, "done": True})
            
            else:
                error = {
                    "error": f"API error: {response.status_code}",
                    "details": response.text
                }
                self.last_response = error
                print(f"⚠️ API error: {response.status_code} - {response.text}")
                if callback:
                    callback(error)
        
        except Exception as e:
            error = {"error": f"Request failed: {str(e)}"}
            self.last_response = error
            print(f"⚠️ Request failed: {e}")
            if callback:
                callback(error)
    
    def transcribe_audio(self, audio_file: str) -> Dict[str, Any]:
        """
        Transcribe audio using OpenRouter API
        
        Args:
            audio_file: Path to audio file
        
        Returns:
            Response from OpenRouter API
        """
        if not self.api_key:
            print("⚠️ API key not set")
            return {"error": "API key not set"}
        
        try:
            if not os.path.exists(audio_file):
                return {"error": f"Audio file not found: {audio_file}"}
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://renz-assistant.app",  # Replace with your app's URL
                "X-Title": "Renz Assistant"
            }
            
            with open(audio_file, "rb") as f:
                files = {
                    "file": (os.path.basename(audio_file), f, "audio/wav")
                }
                
                response = requests.post(
                    f"{self.BASE_URL}/audio/transcriptions",
                    headers=headers,
                    files=files,
                    data={"model": "whisper-1"}
                )
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                print(f"⚠️ API error: {response.status_code} - {response.text}")
                return {
                    "error": f"API error: {response.status_code}",
                    "details": response.text
                }
        
        except Exception as e:
            print(f"⚠️ Request failed: {e}")
            return {"error": f"Request failed: {str(e)}"}
    
    def get_embedding(self, text: str, model: str = "text-embedding-ada-002") -> Dict[str, Any]:
        """
        Get embedding for text using OpenRouter API
        
        Args:
            text: Text to embed
            model: Model to use
        
        Returns:
            Response from OpenRouter API
        """
        if not self.api_key:
            print("⚠️ API key not set")
            return {"error": "API key not set"}
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://renz-assistant.app",  # Replace with your app's URL
                "X-Title": "Renz Assistant"
            }
            
            data = {
                "model": model,
                "input": text
            }
            
            response = requests.post(
                f"{self.BASE_URL}/embeddings",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                print(f"⚠️ API error: {response.status_code} - {response.text}")
                return {
                    "error": f"API error: {response.status_code}",
                    "details": response.text
                }
        
        except Exception as e:
            print(f"⚠️ Request failed: {e}")
            return {"error": f"Request failed: {str(e)}"}


class AIAssistant:
    """AI Assistant using OpenRouter API"""
    
    def __init__(self, client: OpenRouterClient = None, system_prompt: str = None):
        """Initialize AI Assistant"""
        self.client = client or OpenRouterClient()
        self.system_prompt = system_prompt or "You are a helpful assistant."
        self.conversation_history = []
        self.max_history = 20
        
        # Initialize conversation with system prompt
        self.reset_conversation()
    
    def reset_conversation(self) -> None:
        """Reset conversation history"""
        self.conversation_history = [
            {"role": "system", "content": self.system_prompt}
        ]
    
    def set_system_prompt(self, prompt: str) -> None:
        """Set system prompt"""
        self.system_prompt = prompt
        
        # Update system prompt in conversation history
        if self.conversation_history and self.conversation_history[0]["role"] == "system":
            self.conversation_history[0]["content"] = prompt
        else:
            self.conversation_history.insert(0, {"role": "system", "content": prompt})
    
    def add_user_message(self, message: str) -> None:
        """Add user message to conversation history"""
        self.conversation_history.append({"role": "user", "content": message})
        
        # Trim history if needed
        if len(self.conversation_history) > self.max_history + 1:  # +1 for system prompt
            # Keep system prompt and trim oldest messages
            self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-(self.max_history):]
    
    def add_assistant_message(self, message: str) -> None:
        """Add assistant message to conversation history"""
        self.conversation_history.append({"role": "assistant", "content": message})
        
        # Trim history if needed
        if len(self.conversation_history) > self.max_history + 1:  # +1 for system prompt
            # Keep system prompt and trim oldest messages
            self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-(self.max_history):]
    
    def get_response(
        self,
        user_message: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Get response from AI Assistant
        
        Args:
            user_message: User message (if None, uses existing conversation history)
            model: Model to use (defaults to client's default_model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum number of tokens to generate
        
        Returns:
            Assistant's response
        """
        if user_message:
            self.add_user_message(user_message)
        
        response = self.client.chat_completion(
            messages=self.conversation_history,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        if "error" in response:
            return f"Error: {response.get('error')}"
        
        try:
            assistant_message = response["choices"][0]["message"]["content"]
            self.add_assistant_message(assistant_message)
            return assistant_message
        except (KeyError, IndexError):
            return "Error: Failed to parse response"
    
    def stream_response(
        self,
        user_message: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        callback=None
    ) -> None:
        """
        Stream response from AI Assistant
        
        Args:
            user_message: User message (if None, uses existing conversation history)
            model: Model to use (defaults to client's default_model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum number of tokens to generate
            callback: Function to call with each chunk of the response
        """
        if user_message:
            self.add_user_message(user_message)
        
        full_response = ""
        
        def handle_chunk(chunk):
            nonlocal full_response
            
            if "error" in chunk:
                if callback:
                    callback(f"Error: {chunk.get('error')}")
                return
            
            if "content" in chunk:
                if callback:
                    callback(chunk["content"])
            
            if "full_response" in chunk:
                full_response = chunk["full_response"]
            
            if chunk.get("done", False) and full_response:
                self.add_assistant_message(full_response)
        
        self.client.stream_chat_completion(
            messages=self.conversation_history,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            callback=handle_chunk
        )