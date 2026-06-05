from pydantic import BaseModel, Field
from typing import List


class IncidentContext(BaseModel):
    """
    Holds the state and data for a single incident execution flow.
    Must be fully serializable for transport through Kafka and databases.
    """

    incident_id: str = Field(default="unknown")
    alert_name: str = Field(default="Unknown Alert")
    summary: str = Field(default="No summary provided.")

    # Store clean data instead of huge strings
    enriched_data: List[str] = Field(default_factory=list)
    execution_steps: List[str] = Field(default_factory=list)
    screenshots: List[str] = Field(default_factory=list)
    ai_output: str = Field(default="No AI analysis performed.")

    def add_enrichment(self, data: str):
        self.enriched_data.append(data)

    def add_step(self, step: str):
        self.execution_steps.append(step)

    def add_screenshot(self, path: str):
        if path and path not in self.screenshots:
            self.screenshots.append(path)

    def format_for_ai(self) -> str:
        """Formats the context into a string optimized for AI consumption."""
        formatted = f"Summary: {self.summary}\n"
        if self.enriched_data:
            formatted += "\n--- Context Data ---\n"
            formatted += "\n".join(self.enriched_data)
        return formatted

    def format_report(self) -> str:
        """Formats the final human-readable report."""
        steps_str = (
            "\n".join(self.execution_steps)
            if self.execution_steps
            else "No execution steps recorded."
        )
        context_str = (
            "\n".join(self.enriched_data)
            if self.enriched_data
            else "No additional context."
        )

        return (
            f"INCIDENT REPORT: {self.alert_name}\n"
            f"{'=' * 40}\n"
            f"CRITICAL SUMMARY:\n{self.summary}\n\n"
            f"AUTOMATED EXECUTION LOG:\n{steps_str}\n\n"
            f"LIVE SYSTEM CONTEXT:\n{context_str}\n\n"
            f"AI RECOMMENDATIONS & RCA:\n{self.ai_output}\n"
            f"{'=' * 40}\n"
            f"Status: This report was generated automatically by the AI-Responder Bot."
        )
