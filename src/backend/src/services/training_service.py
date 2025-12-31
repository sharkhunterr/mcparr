"""Training service supporting Ollama Modelfile-based training and Unsloth fine-tuning."""

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import httpx
from loguru import logger


class TrainingBackend(str, Enum):
    """Available training backends."""

    OLLAMA_MODELFILE = "ollama_modelfile"  # Modelfile with embedded examples (no GPU needed)
    UNSLOTH = "unsloth"  # Fast, memory efficient fine-tuning (GPU required)
    TRANSFORMERS = "transformers"  # Standard HuggingFace
    MLXLM = "mlx-lm"  # For Apple Silicon


@dataclass
class OllamaModelfileConfig:
    """Configuration for Ollama Modelfile-based training."""

    base_model: str = "llama3.2:3b"  # Base Ollama model
    output_model_name: str = "mcparr-trained"
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    num_ctx: int = 4096  # Context window
    num_predict: int = 1024  # Max tokens to generate

    # System prompt components
    base_system_prompt: str = """Tu es MCParr, un assistant IA spécialisé pour la gestion d'un homelab.
Tu utilises les outils MCP disponibles pour interagir avec les services du homelab.
Tu réponds toujours en français sauf si on te demande explicitement l'anglais.
Tu es précis, concis et utile."""


@dataclass
class TrainingConfig:
    """Configuration for fine-tuning (Unsloth/Transformers)."""

    # Model
    base_model: str = "unsloth/llama-3.2-3b-instruct-bnb-4bit"
    max_seq_length: int = 2048
    load_in_4bit: bool = True

    # LoRA config
    lora_r: int = 16
    lora_alpha: int = 16
    lora_dropout: float = 0.0

    # Training
    batch_size: int = 2
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    num_epochs: int = 1
    max_steps: int = -1  # -1 means use epochs
    warmup_steps: int = 5
    weight_decay: float = 0.01

    # Output
    output_dir: str = "/tmp/mcparr_training"
    output_model_name: str = "mcparr-finetuned"
    quantization: str = "q4_k_m"  # For GGUF export


class TrainingService:
    """Service for training LLMs via Ollama Modelfile or local fine-tuning."""

    def __init__(self, ollama_url: str = "http://localhost:11434", training_dir: Optional[str] = None):
        self.ollama_url = ollama_url
        self.training_dir = Path(training_dir or "/tmp/mcparr_training")
        self.training_dir.mkdir(parents=True, exist_ok=True)
        self._current_process: Optional[subprocess.Popen] = None
        self._progress_callback: Optional[Callable] = None
        self._cancel_requested: bool = False

    # ============= Ollama Modelfile-based Training =============

    def generate_enriched_system_prompt(self, prompts: List[Dict[str, Any]], config: OllamaModelfileConfig) -> str:
        """Generate a system prompt enriched with training examples."""
        examples_text = []

        for i, prompt in enumerate(prompts, 1):
            user_input = prompt.get("user_input", "")
            expected_output = prompt.get("expected_output", "")

            # Format each example
            example = f"""
### Exemple {i}:
**Utilisateur**: {user_input}
**Réponse attendue**: {expected_output}"""
            examples_text.append(example)

        # Build the enriched system prompt
        enriched_prompt = f"""{config.base_system_prompt}

## Exemples de comportement attendu

Voici des exemples de la façon dont tu dois répondre aux requêtes:
{''.join(examples_text)}

## Instructions

En te basant sur ces exemples, tu dois:
1. Utiliser les outils MCP appropriés quand c'est nécessaire
2. Répondre de manière structurée et précise
3. Fournir les informations demandées de façon claire"""

        return enriched_prompt

    def generate_modelfile(self, prompts: List[Dict[str, Any]], config: OllamaModelfileConfig) -> str:
        """Generate Ollama Modelfile content with embedded training examples."""
        enriched_system = self.generate_enriched_system_prompt(prompts, config)

        # Escape quotes for Modelfile
        enriched_system.replace('"', '\\"')

        modelfile = f'''FROM {config.base_model}

# Parameters
PARAMETER temperature {config.temperature}
PARAMETER top_p {config.top_p}
PARAMETER top_k {config.top_k}
PARAMETER num_ctx {config.num_ctx}
PARAMETER num_predict {config.num_predict}

# System prompt with embedded training examples
SYSTEM """
{enriched_system}
"""
'''
        return modelfile

    async def create_ollama_model(
        self,
        prompts: List[Dict[str, Any]],
        config: Optional[OllamaModelfileConfig] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Create a new Ollama model via the /api/create endpoint."""
        config = config or OllamaModelfileConfig()
        self._cancel_requested = False

        logger.info(f"Creating Ollama model '{config.output_model_name}' with {len(prompts)} training examples")

        # Generate enriched system prompt with examples
        enriched_system = self.generate_enriched_system_prompt(prompts, config)

        # Also generate Modelfile content for reference
        modelfile_content = self.generate_modelfile(prompts, config)

        # Save Modelfile locally for reference
        modelfile_path = self.training_dir / f"Modelfile_{config.output_model_name}"
        with open(modelfile_path, "w", encoding="utf-8") as f:
            f.write(modelfile_content)

        logger.debug(f"Modelfile saved to {modelfile_path}")

        if progress_callback:
            await self._call_progress(
                progress_callback,
                {
                    "step": 1,
                    "total_steps": 3,
                    "progress_percent": 10,
                    "status": "preparing",
                    "message": "Generating system prompt...",
                },
            )

        try:
            # Call Ollama API to create the model
            # Note: Uses 'from' and 'system' fields for compatibility with older Ollama versions
            async with httpx.AsyncClient(timeout=600.0) as client:
                if progress_callback:
                    await self._call_progress(
                        progress_callback,
                        {
                            "step": 2,
                            "total_steps": 3,
                            "progress_percent": 30,
                            "status": "creating",
                            "message": "Creating model on Ollama server...",
                        },
                    )

                # Build request with 'from' and 'system' fields for compatibility
                # This works with older Ollama versions (0.13+) and newer ones
                create_request = {
                    "name": config.output_model_name,
                    "from": config.base_model,
                    "system": enriched_system,
                    "stream": True,
                    "parameters": {
                        "temperature": config.temperature,
                        "top_p": config.top_p,
                        "top_k": config.top_k,
                        "num_ctx": config.num_ctx,
                        "num_predict": config.num_predict,
                    },
                }

                logger.debug(f"Ollama create request: name={config.output_model_name}, from={config.base_model}")

                # Stream the response
                async with client.stream("POST", f"{self.ollama_url}/api/create", json=create_request) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        return {
                            "success": False,
                            "error": f"Ollama API error: {response.status_code} - {error_text.decode()}",
                        }

                    last_status = ""
                    async for line in response.aiter_lines():
                        if self._cancel_requested:
                            return {"success": False, "error": "Training cancelled"}

                        if line:
                            try:
                                data = json.loads(line)
                                status = data.get("status", "")

                                if status != last_status:
                                    last_status = status
                                    logger.debug(f"Ollama create status: {status}")

                                    if progress_callback:
                                        # Estimate progress based on status messages
                                        progress = 30
                                        if "pulling" in status.lower():
                                            progress = 40
                                        elif "verifying" in status.lower():
                                            progress = 70
                                        elif "writing" in status.lower():
                                            progress = 85
                                        elif "success" in status.lower():
                                            progress = 100

                                        await self._call_progress(
                                            progress_callback,
                                            {
                                                "step": 2,
                                                "total_steps": 3,
                                                "progress_percent": progress,
                                                "status": "creating",
                                                "message": status,
                                            },
                                        )

                                if data.get("error"):
                                    return {"success": False, "error": data["error"]}

                            except json.JSONDecodeError:
                                continue

            if progress_callback:
                await self._call_progress(
                    progress_callback,
                    {
                        "step": 3,
                        "total_steps": 3,
                        "progress_percent": 100,
                        "status": "completed",
                        "message": f"Model '{config.output_model_name}' created successfully!",
                    },
                )

            return {
                "success": True,
                "model_name": config.output_model_name,
                "base_model": config.base_model,
                "prompts_count": len(prompts),
                "modelfile_path": str(modelfile_path),
                "message": (
                    f"Model '{config.output_model_name}' created successfully " f"with {len(prompts)} embedded examples"
                ),
            }

        except httpx.ConnectError as e:
            return {"success": False, "error": f"Cannot connect to Ollama at {self.ollama_url}: {e}"}
        except httpx.TimeoutException:
            return {"success": False, "error": "Timeout while creating model"}
        except Exception as e:
            logger.error(f"Failed to create Ollama model: {e}")
            return {"success": False, "error": str(e)}

    async def _call_progress(self, callback: Callable[[Dict[str, Any]], None], progress: Dict[str, Any]):
        """Call progress callback safely."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(progress)
            else:
                await asyncio.get_event_loop().run_in_executor(None, callback, progress)
        except Exception as e:
            logger.warning(f"Progress callback error: {e}")

    async def list_ollama_models(self) -> List[Dict[str, Any]]:
        """List all models available on Ollama."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("models", [])
                return []
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def delete_ollama_model(self, model_name: str) -> Dict[str, Any]:
        """Delete a model from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(f"{self.ollama_url}/api/delete", json={"name": model_name})
                if response.status_code == 200:
                    return {"success": True, "message": f"Model '{model_name}' deleted"}
                else:
                    return {"success": False, "error": f"Failed to delete: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============= Unsloth Fine-tuning (requires GPU) =============

    async def check_requirements(self) -> Dict[str, Any]:
        """Check if training requirements are met."""
        results = {
            "gpu_available": False,
            "gpu_name": None,
            "gpu_memory_gb": 0,
            "cuda_available": False,
            "unsloth_available": False,
            "transformers_available": False,
            "ollama_available": False,
            "recommended_backend": None,
            "errors": [],
        }

        # Check GPU
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(",")
                results["gpu_available"] = True
                results["gpu_name"] = parts[0].strip()
                results["gpu_memory_gb"] = round(float(parts[1].strip()) / 1024, 2)
        except Exception as e:
            results["errors"].append(f"GPU check failed: {e}")

        # Check CUDA
        try:
            result = subprocess.run(
                ["python3", "-c", "import torch; print(torch.cuda.is_available())"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            results["cuda_available"] = result.stdout.strip() == "True"
        except Exception as e:
            results["errors"].append(f"CUDA check failed: {e}")

        # Check Unsloth
        try:
            result = subprocess.run(
                ["python3", "-c", 'import unsloth; print("ok")'], capture_output=True, text=True, timeout=10
            )
            results["unsloth_available"] = result.stdout.strip() == "ok"
        except Exception:
            pass

        # Check transformers
        try:
            result = subprocess.run(
                ["python3", "-c", 'import transformers; print("ok")'], capture_output=True, text=True, timeout=10
            )
            results["transformers_available"] = result.stdout.strip() == "ok"
        except Exception:
            pass

        # Check Ollama
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.ollama_url}/api/version", timeout=5)
                results["ollama_available"] = response.status_code == 200
        except Exception:
            pass

        # Recommend backend
        if results["unsloth_available"] and results["cuda_available"]:
            results["recommended_backend"] = "unsloth"
        elif results["transformers_available"]:
            results["recommended_backend"] = "transformers"

        return results

    def prepare_training_data(self, prompts: List[Dict[str, Any]], output_path: Optional[Path] = None) -> Path:
        """Convert prompts to training format (ShareGPT/Chat format)."""
        output_path = output_path or self.training_dir / "training_data.jsonl"

        training_data = []
        for prompt in prompts:
            # Convert to chat format
            conversation = {"conversations": []}

            # Add system prompt if present
            if prompt.get("system_prompt"):
                conversation["conversations"].append({"from": "system", "value": prompt["system_prompt"]})

            # Add user input
            conversation["conversations"].append({"from": "human", "value": prompt["user_input"]})

            # Add expected output
            conversation["conversations"].append({"from": "gpt", "value": prompt["expected_output"]})

            training_data.append(conversation)

        # Write JSONL
        with open(output_path, "w", encoding="utf-8") as f:
            for item in training_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        logger.info(f"Prepared {len(training_data)} training examples at {output_path}")
        return output_path

    def generate_training_script(self, config: TrainingConfig, data_path: Path) -> Path:
        """Generate Python training script for Unsloth."""
        script_path = self.training_dir / "train.py"

        script = f'''#!/usr/bin/env python3
"""Auto-generated training script for MCParr fine-tuning."""

import os
import json
from datetime import datetime

# Suppress warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

def main():
    print("=" * 60)
    print("MCParr Fine-Tuning with Unsloth")
    print("=" * 60)

    # Import after env setup
    from unsloth import FastLanguageModel
    from datasets import load_dataset
    from trl import SFTTrainer
    from transformers import TrainingArguments
    from unsloth.chat_templates import get_chat_template

    # Configuration
    model_name = "{config.base_model}"
    max_seq_length = {config.max_seq_length}

    print(f"Loading model: {{model_name}}")

    # Load model with 4-bit quantization
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        dtype=None,  # Auto-detect
        load_in_4bit={str(config.load_in_4bit)},
    )

    print("Configuring LoRA adapters...")

    # Configure LoRA
    model = FastLanguageModel.get_peft_model(
        model,
        r={config.lora_r},
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                       "gate_proj", "up_proj", "down_proj"],
        lora_alpha={config.lora_alpha},
        lora_dropout={config.lora_dropout},
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # Setup chat template
    tokenizer = get_chat_template(
        tokenizer,
        chat_template="llama-3.1",
    )

    print("Loading training data...")

    # Load dataset
    dataset = load_dataset(
        "json",
        data_files="{data_path}",
        split="train"
    )

    print(f"Loaded {{len(dataset)}} training examples")

    def formatting_prompts_func(examples):
        convos = examples["conversations"]
        texts = []
        for convo in convos:
            messages = []
            for turn in convo:
                role = "user" if turn["from"] == "human" else "assistant"
                if turn["from"] == "system":
                    role = "system"
                messages.append({{"role": role, "content": turn["value"]}})
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            texts.append(text)
        return {{"text": texts}}

    dataset = dataset.map(formatting_prompts_func, batched=True)

    print("Starting training...")

    # Training arguments
    training_args = TrainingArguments(
        per_device_train_batch_size={config.batch_size},
        gradient_accumulation_steps={config.gradient_accumulation_steps},
        warmup_steps={config.warmup_steps},
        max_steps={config.max_steps if config.max_steps > 0 else -1},
        num_train_epochs={config.num_epochs if config.max_steps <= 0 else 1},
        learning_rate={config.learning_rate},
        fp16=True,
        logging_steps=1,
        optim="adamw_8bit",
        weight_decay={config.weight_decay},
        lr_scheduler_type="linear",
        seed=42,
        output_dir="{config.output_dir}",
        report_to="none",
    )

    # Create trainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        dataset_num_proc=2,
        packing=False,
        args=training_args,
    )

    # Train
    stats = trainer.train()

    print("\\nTraining complete!")
    print(f"Training loss: {{stats.training_loss:.4f}}")

    # Save model
    print("\\nSaving model...")
    model.save_pretrained("{config.output_dir}/lora_model")
    tokenizer.save_pretrained("{config.output_dir}/lora_model")

    # Export to GGUF
    print("\\nExporting to GGUF format...")
    model.save_pretrained_gguf(
        "{config.output_dir}/gguf",
        tokenizer,
        quantization_method="{config.quantization}",
    )

    # Create Modelfile for Ollama
    modelfile_content = f"""FROM {config.output_dir}/gguf/unsloth.{config.quantization.upper()}.gguf

TEMPLATE \"\"\"{{{{- if .System }}}}
<|start_header_id|>system<|end_header_id|>

{{{{ .System }}}}<|eot_id|>
{{{{- end }}}}
<|start_header_id|>user<|end_header_id|>

{{{{ .Prompt }}}}<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>

{{{{ .Response }}}}<|eot_id|>\"\"\"

PARAMETER stop "<|start_header_id|>"
PARAMETER stop "<|end_header_id|>"
PARAMETER stop "<|eot_id|>"

SYSTEM "Tu es MCParr, un assistant IA spécialisé pour le homelab. \
Tu utilises les outils MCP disponibles pour interagir avec les services."
"""

    with open("{config.output_dir}/Modelfile", "w") as f:
        f.write(modelfile_content)

    print(f"\\nModelfile created at {config.output_dir}/Modelfile")

    # Write completion marker
    with open("{config.output_dir}/training_complete.json", "w") as f:
        json.dump({{
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "training_loss": stats.training_loss,
            "model_path": "{config.output_dir}/gguf",
            "modelfile_path": "{config.output_dir}/Modelfile"
        }}, f)

    print("\\n" + "=" * 60)
    print("Training complete! To use with Ollama:")
    print(f"  ollama create {config.output_model_name} -f {config.output_dir}/Modelfile")
    print(f"  ollama run {config.output_model_name}")
    print("=" * 60)


if __name__ == "__main__":
    main()
'''

        with open(script_path, "w") as f:
            f.write(script)

        os.chmod(script_path, 0o755)
        logger.info(f"Generated training script at {script_path}")
        return script_path

    async def start_training(
        self,
        prompts: List[Dict[str, Any]],
        config: Optional[TrainingConfig] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Start the training process."""
        config = config or TrainingConfig()
        self._progress_callback = progress_callback

        # Prepare data
        data_path = self.prepare_training_data(prompts)

        # Generate script
        script_path = self.generate_training_script(config, data_path)

        # Run training in subprocess
        logger.info("Starting training process...")

        try:
            self._current_process = subprocess.Popen(
                ["python3", str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(self.training_dir),
            )

            output_lines = []
            current_step = 0
            total_steps = config.max_steps if config.max_steps > 0 else len(prompts) * config.num_epochs

            while True:
                line = self._current_process.stdout.readline()
                if not line and self._current_process.poll() is not None:
                    break

                if line:
                    output_lines.append(line.strip())
                    logger.debug(f"Training: {line.strip()}")

                    # Parse progress
                    if "loss" in line.lower() and progress_callback:
                        current_step += 1
                        progress = {
                            "step": current_step,
                            "total_steps": total_steps,
                            "progress_percent": min(100, (current_step / max(1, total_steps)) * 100),
                            "output": line.strip(),
                        }
                        # Extract loss if possible
                        try:
                            if "'loss':" in line:
                                import re

                                loss_match = re.search(r"'loss':\s*([\d.]+)", line)
                                if loss_match:
                                    progress["loss"] = float(loss_match.group(1))
                        except Exception:
                            pass

                        await asyncio.get_event_loop().run_in_executor(None, progress_callback, progress)

            return_code = self._current_process.poll()

            # Check for completion
            completion_file = Path(config.output_dir) / "training_complete.json"
            if completion_file.exists():
                with open(completion_file) as f:
                    result = json.load(f)
                result["success"] = True
                result["output"] = output_lines[-50:]  # Last 50 lines
                return result
            else:
                return {
                    "success": return_code == 0,
                    "return_code": return_code,
                    "output": output_lines[-50:],
                    "error": "Training did not complete successfully" if return_code != 0 else None,
                }

        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            self._current_process = None

    async def import_to_ollama(self, model_name: str, modelfile_path: Optional[str] = None) -> Dict[str, Any]:
        """Import the fine-tuned model into Ollama."""
        modelfile_path = modelfile_path or str(self.training_dir / "Modelfile")

        if not Path(modelfile_path).exists():
            return {"success": False, "error": f"Modelfile not found: {modelfile_path}"}

        try:
            # Create model in Ollama
            result = subprocess.run(
                ["ollama", "create", model_name, "-f", modelfile_path],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
            )

            if result.returncode == 0:
                logger.info(f"Successfully imported model '{model_name}' to Ollama")
                return {"success": True, "model_name": model_name, "output": result.stdout}
            else:
                return {"success": False, "error": result.stderr or "Failed to create model", "output": result.stdout}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout while importing model"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cancel_training(self) -> bool:
        """Cancel the current training process."""
        self._cancel_requested = True
        if self._current_process:
            self._current_process.terminate()
            try:
                self._current_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._current_process.kill()
            self._current_process = None
            return True
        return self._cancel_requested

    def get_training_status(self) -> Dict[str, Any]:
        """Get current training status."""
        if self._current_process:
            poll = self._current_process.poll()
            if poll is None:
                return {"status": "running"}
            else:
                return {"status": "completed", "return_code": poll}
        return {"status": "idle"}
