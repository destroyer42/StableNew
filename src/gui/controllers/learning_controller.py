from __future__ import annotations

from typing import Any, Optional

from src.gui.learning_state import LearningExperiment, LearningState, LearningVariant
from src.gui.prompt_workspace_state import PromptWorkspaceState


class LearningController:
    """Controller for learning experiment workflows."""

    def __init__(
        self,
        learning_state: LearningState,
        prompt_workspace_state: Optional[PromptWorkspaceState] = None,
        pipeline_state: Optional[Any] = None,  # Placeholder for PipelineState
        pipeline_controller: Optional[Any] = None,  # PipelineController reference
        plan_table: Optional[Any] = None,  # LearningPlanTable reference
        review_panel: Optional[Any] = None,  # LearningReviewPanel reference
    ) -> None:
        self.learning_state = learning_state
        self.prompt_workspace_state = prompt_workspace_state
        self.pipeline_state = pipeline_state
        self.pipeline_controller = pipeline_controller
        self._plan_table = plan_table
        self._review_panel = review_panel

    def update_experiment_design(self, experiment_data: dict[str, Any]) -> None:
        """Update the current experiment design from form data."""
        # Create LearningExperiment from form data
        experiment = LearningExperiment(
            name=experiment_data.get("name", ""),
            description=experiment_data.get("description", ""),
            baseline_config={},  # Will be populated from pipeline state later
            prompt_text=experiment_data.get("custom_prompt", "") if experiment_data.get("prompt_source") == "custom" else "",
            stage=experiment_data.get("stage", "txt2img"),
            variable_under_test=experiment_data.get("variable_under_test", ""),
            values=self._generate_values_from_range(
                experiment_data.get("start_value", 1.0),
                experiment_data.get("end_value", 10.0),
                experiment_data.get("step_value", 1.0)
            ),
            images_per_value=experiment_data.get("images_per_value", 1),
        )

        # Store in state
        self.learning_state.current_experiment = experiment

    def _generate_values_from_range(self, start: float, end: float, step: float) -> list[float]:
        """Generate list of values from start to end with given step."""
        values = []
        current = start
        while current <= end:
            values.append(round(current, 2))
            current += step
        return values

    def build_plan(self, experiment: LearningExperiment) -> None:
        """Build a learning plan from experiment definition."""
        from src.gui.learning_state import LearningVariant

        # Store the current experiment
        self.learning_state.current_experiment = experiment

        # Clear any existing plan
        self.learning_state.plan = []

        # Generate variants for each value in the experiment
        for i, value in enumerate(experiment.values):
            variant = LearningVariant(
                experiment_id=experiment.name,  # Use experiment name as ID for now
                param_value=value,
                status="pending",
                planned_images=experiment.images_per_value,
                completed_images=0,
                image_refs=[]
            )
            self.learning_state.plan.append(variant)

        # Update the plan table if it exists
        if self._plan_table:
            self._update_plan_table()

    def _update_plan_table(self) -> None:
        """Update the learning plan table with current plan data."""
        if self._plan_table and hasattr(self._plan_table, 'update_plan'):
            self._plan_table.update_plan(self.learning_state.plan)

    def run_plan(self) -> None:
        """Execute the current learning plan."""
        if not self.learning_state.plan:
            return

        if not self.pipeline_controller:
            return

        # Submit jobs for each variant
        for variant in self.learning_state.plan:
            if variant.status == "pending":
                self._submit_variant_job(variant)

        # Update table
        self._update_plan_table()

    def _submit_variant_job(self, variant: LearningVariant) -> None:
        """Submit a pipeline job for a single learning variant."""
        if not self.learning_state.current_experiment or not self.pipeline_controller:
            return

        experiment = self.learning_state.current_experiment

        # Build overrides for this variant based on variable_under_test
        overrides = self._build_variant_overrides(variant, experiment)

        # Submit the job
        try:
            success = self.pipeline_controller.start_pipeline(
                pipeline_func=None,
                on_complete=lambda result: self._on_variant_job_completed(variant, result),
                on_error=lambda error: self._on_variant_job_failed(variant, error)
            )

            if success and variant.status != "completed":
                variant.status = "running"
            else:
                variant.status = "failed"

        except Exception as e:
            variant.status = "failed"

    def _build_variant_overrides(self, variant: LearningVariant, experiment: LearningExperiment) -> dict[str, Any]:
        """Build pipeline overrides for a learning variant."""
        overrides = {}

        # Apply the variable under test
        variable = experiment.variable_under_test
        value = variant.param_value

        if variable == "CFG Scale":
            overrides["cfg_scale"] = value
        elif variable == "Steps":
            overrides["steps"] = int(value)
        elif variable == "Sampler":
            overrides["sampler"] = str(value)
        elif variable == "Scheduler":
            overrides["scheduler"] = str(value)
        elif variable.startswith("LoRA Strength"):
            # For LoRA strength, we'd need to handle this differently
            # For now, just store the value
            overrides["lora_strength"] = value
        elif variable == "Denoise Strength":
            overrides["denoise_strength"] = value
        elif variable == "Upscale Factor":
            overrides["upscale_factor"] = value

        # Add learning context
        overrides["learning_experiment_id"] = experiment.name
        overrides["learning_variant_value"] = value
        overrides["learning_variable"] = variable

        return overrides

    def _on_variant_job_completed(self, variant: LearningVariant, result: dict[str, Any]) -> None:
        """Handle completion of a variant job."""
        variant.status = "completed"
        variant.completed_images += 1

        # Extract image references from result
        if "images" in result:
            for image_path in result["images"]:
                variant.image_refs.append(image_path)

        # Update UI
        self._update_plan_table()

        # Update review panel if this variant is selected
        if self._review_panel and hasattr(self._review_panel, 'display_variant_results'):
            self._review_panel.display_variant_results(variant)

    def _on_variant_job_failed(self, variant: LearningVariant, error: Exception) -> None:
        """Handle failure of a variant job."""
        variant.status = "failed"

        # Update UI
        self._update_plan_table()

    def on_job_completed(self, job_id: str, result: dict[str, Any]) -> None:
        """Handle completion of a learning job."""
        # This method can be used for general job completion handling
        # The specific variant handling is done in _on_variant_job_completed
        pass

    def record_rating(self, image_ref: str, rating: int, notes: str = "") -> None:
        """Record a rating for a learning image."""
        # Placeholder - no implementation yet
        pass