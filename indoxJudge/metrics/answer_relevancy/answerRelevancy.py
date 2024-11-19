from typing import List, Optional
from pydantic import BaseModel, Field
import json

from .template import AnswerRelevancyTemplate
from loguru import logger
import sys

# Set up logging
logger.remove()  # Remove the default logger
logger.add(
    sys.stdout, format="<green>{level}</green>: <level>{message}</level>", level="INFO"
)

logger.add(
    sys.stdout, format="<red>{level}</red>: <level>{message}</level>", level="ERROR"
)


class Statements(BaseModel):
    """
    Model representing a list of statements extracted from the LLM response.
    """

    statements: List[str]


class AnswerRelevancyVerdict(BaseModel):
    """
    Model representing a verdict on the relevancy of an answer,
    including the verdict itself and the reasoning behind it.
    """

    verdict: str
    reason: str = Field(default=None)


class Verdicts(BaseModel):
    """
    Model representing a list of AnswerRelevancyVerdict instances.
    """

    verdicts: List[AnswerRelevancyVerdict]


class Reason(BaseModel):
    """
    Model representing the reason provided for any irrelevant statements found in the response.
    """

    reason: str


class AnswerRelevancy:
    """
    Class for evaluating the relevancy of language model outputs by analyzing statements,
    generating verdicts, and calculating relevancy scores.
    """

    def __init__(
        self,
        query: str,
        llm_response: str,
        threshold: float = 0.5,
        include_reason: bool = True,
        strict_mode: bool = False,
    ):
        """
        Initializes the AnswerRelevancy class with the query, LLM response, and evaluation settings.

        :param query: The query being evaluated.
        :param llm_response: The response generated by the language model.
        :param threshold: The threshold for determining relevancy. Defaults to 0.5.
        :param include_reason: Whether to include reasoning for the relevancy verdicts. Defaults to True.
        :param strict_mode: Whether to use strict mode, which forces a score of 0 if relevancy is below the threshold. Defaults to False.
        """
        self.model = None
        self.query = query
        self.llm_response = llm_response
        self.threshold = 1 if strict_mode else threshold
        self.include_reason = include_reason
        self.strict_mode = strict_mode
        self.evaluation_cost = None
        self.statements = []
        self.verdicts = []
        self.reason = None
        self.score = 0
        self.success = False
        self.total_output_tokens = 0
        self.total_input_tokens = 0

    def set_model(self, model):
        """
        Sets the language model to be used for evaluation.

        :param model: The language model to use.
        """
        self.model = model

    def measure(self) -> float:
        """
        Measures the relevancy of the LLM response by generating statements, verdicts, and reasons,
        then calculating the relevancy score.

        :return: The calculated relevancy score.
        """
        self.statements = self._generate_statements()
        self.verdicts = self._generate_verdicts()
        self.score = self._calculate_score()
        self.reason = self._generate_reason(self.query)
        self.success = self.score >= self.threshold
        logger.info(
            f"Token Usage Summary:\n Total Input: {self.total_input_tokens} | Total Output: {self.total_output_tokens} | Total: {self.total_input_tokens + self.total_output_tokens}"
        )
        return self.score

    def _generate_statements(self) -> List[str]:
        """
        Generates a list of statements from the LLM response using a prompt template.

        :return: A list of statements.
        """
        prompt = AnswerRelevancyTemplate.generate_statements(
            llm_response=self.llm_response
        )
        response = self._call_language_model(prompt)
        data = json.loads(response)
        return data["statements"]

    def _generate_verdicts(self) -> List[AnswerRelevancyVerdict]:
        """
        Generates a list of verdicts on the relevancy of the statements.

        :return: A list of AnswerRelevancyVerdict instances.
        """
        prompt = AnswerRelevancyTemplate.generate_verdicts(
            query=self.query, llm_response=self.statements
        )
        response = self._call_language_model(prompt)
        data = json.loads(response)
        return [AnswerRelevancyVerdict(**item) for item in data["verdicts"]]

    def _generate_reason(self, query: str) -> Optional[str]:
        if not self.include_reason:
            return None

        irrelevant_statements = [
            verdict.reason
            for verdict in self.verdicts
            if verdict.verdict.strip().lower() == "no"
        ]

        prompt = AnswerRelevancyTemplate.generate_reason(
            irrelevant_statements=irrelevant_statements,
            query=query,
            score=format(self.score, ".2f"),
        )

        response = self._call_language_model(prompt)
        data = json.loads(response)
        return data["reason"]

    def _calculate_score(self) -> float:
        if len(self.verdicts) == 0:
            return 1.0  # If no verdicts, assume full relevancy by default.

        verdict = self.verdicts[0].verdict.strip().lower()

        if verdict == "yes":
            score = 1.0
        elif verdict == "idk":
            score = 0.5
        elif verdict == "no":
            score = 0.0
        else:
            score = 0.0  # Default to 0.0 for any unexpected values.

        return score

    def _clean_json_response(self, response: str) -> str:
        """
        Cleans the JSON response from the language model by removing markdown code blocks if present.

        :param response: Raw response from the language model
        :return: Cleaned JSON string
        """
        if response.startswith("```json") and response.endswith("```"):
            response = response[7:-3].strip()
        return response

    def _call_language_model(self, prompt: str) -> str:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        input_token_count = len(enc.encode(prompt))
        response = self.model.generate_evaluation_response(prompt=prompt)
        self.total_input_tokens += input_token_count

        if not response:
            raise ValueError("Received an empty response from the model.")

        clean_response = self._clean_json_response(response=response)
        output_token_count = len(enc.encode(response))
        self.total_output_tokens += output_token_count
        logger.info(
            f"Token Counts - Input: {input_token_count} | Output: {output_token_count}"
        )

        return clean_response
