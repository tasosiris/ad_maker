
import json
from pathlib import Path
from typing import Dict, Any
from src.utils.logger import logger

PRICING_INFO = {
    "openai": {
        "gpt-4o": {"input": 5.00 / 1_000_000, "output": 15.00 / 1_000_000},
    },
    "elevenlabs": { "v2": 0.15 / 1000 }, # per character
    "pexels": { "api_call": 0.0 }, # Free tier, but track calls
    "aimlapi": {
        "kling-video/v1/standard/image-to-video": 0.0315, # per second
        "kling-video/v1/pro/image-to-video": 0.13125, # per second
        "flux/schnell": 0.01 # per image (ASSUMPTION)
    }
}

class CostTracker:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.costs = []

    def add_cost(self, service: str, model: str, **kwargs) -> Dict[str, Any]:
        cost = 0.0
        details = f"Service: {service}, Model: {model}"
        
        if service == "openai":
            if model in PRICING_INFO[service]:
                input_tokens = kwargs.get("tokens_input", 0)
                output_tokens = kwargs.get("tokens_output", 0)
                cost = (input_tokens * PRICING_INFO[service][model]["input"]) + \
                       (output_tokens * PRICING_INFO[service][model]["output"])
                details += f", Input Tokens: {input_tokens}, Output Tokens: {output_tokens}"
        elif service == "elevenlabs":
            characters = kwargs.get("characters", 0)
            cost = characters * PRICING_INFO[service][model]
            details += f", Characters: {characters}"
        elif service == "pexels":
            cost = 0.0 # Free tier
            details += f", API Calls: {kwargs.get('requests', 0)}"
        elif service == "aimlapi":
            if "seconds" in kwargs:
                seconds = kwargs.get("seconds", 0)
                cost = seconds * PRICING_INFO[service][model]
                details += f", Seconds: {seconds}"
            elif "images" in kwargs:
                images = kwargs.get("images", 0)
                cost = images * PRICING_INFO[service][model]
                details += f", Images: {images}"

        cost_info = {"service": service, "model": model, "cost": cost, "details": details}
        self.costs.append(cost_info)
        return cost_info

    def get_last_cost(self) -> Dict[str, Any]:
        return self.costs[-1] if self.costs else {}

    def get_total_cost(self) -> float:
        return sum(c['cost'] for c in self.costs)

    def save_costs(self):
        if not self.costs: return
        total_cost = self.get_total_cost()
        summary_path = self.output_dir / "costs_summary.txt"
        details_path = self.output_dir / "costs_details.json"

        with open(summary_path, "w") as f:
            f.write(f"Total Estimated Cost: ${total_cost:.6f}\n\n")
            f.write("Breakdown:\n")
            for cost_item in self.costs:
                f.write(f"- {cost_item['details']} -> ${cost_item['cost']:.6f}\n")
        
        with open(details_path, "w") as f:
            json.dump(self.costs, f, indent=4)
        
        logger.info(f"Cost report saved to {self.output_dir}") 