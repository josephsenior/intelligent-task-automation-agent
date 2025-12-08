"""
Base agent class providing common functionality for all agents.
"""

import os
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate


class BaseAgent:
    """Base class for all agents in the system."""
    
    def __init__(self, model_name: str = "gpt-4", temperature: float = 0.7):
        """
        Initialize the base agent.
        
        Args:
            model_name: OpenAI model to use
            temperature: Temperature for LLM responses
        """
        from ..utils.openrouter_client import create_llm
        self.llm = create_llm(model_name=model_name, temperature=temperature)
        self.model_name = model_name
        self.temperature = temperature
    
    def _create_prompt(self, template: str, **kwargs) -> ChatPromptTemplate:
        """Create a prompt template."""
        return ChatPromptTemplate.from_template(template)
    
    def _call_llm(self, prompt: str, **kwargs) -> str:
        """
        Call the LLM with a prompt.
        
        Args:
            prompt: The prompt to send
            **kwargs: Additional arguments for the prompt template
            
        Returns:
            LLM response as string
        """
        try:
            messages = [("system", prompt)]
            if kwargs:
                # Format prompt with kwargs if provided
                formatted_prompt = prompt.format(**kwargs)
                messages = [("system", formatted_prompt)]
            
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            raise RuntimeError(f"Error calling LLM: {str(e)}")
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response.
        Attempts to extract JSON even if wrapped in markdown.
        
        Args:
            response: LLM response string
            
        Returns:
            Parsed JSON as dictionary
        """
        import json
        import re
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)
        
        # Try to find JSON object in response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            response = json_match.group(0)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # If JSON parsing fails, return as structured dict
            return {"raw_response": response}
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message (can be overridden for actual logging)."""
        print(f"[{level}] {self.__class__.__name__}: {message}")

