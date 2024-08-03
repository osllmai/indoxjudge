from collections import Counter
from typing import Union, List, Tuple, Dict
import numpy as np
from indoxJudge.utils import TextPreprocessor


class Rouge:
    def __init__(
        self, llm_response: str, retrieval_context: Union[str, List[str]], n: int = 1
    ):
        """
        Initialize the Rouge evaluator with the desired n-gram size.

        Parameters:
        llm_response (str): The response generated by a language model.
        retrieval_context (Union[str, List[str]]): The expected response(s) to compare against the actual response.
        n (int): The size of the n-grams to use for evaluation (e.g., 1 for unigrams, 2 for bigrams, etc.).

        """
        self.llm_response = llm_response
        self.retrieval_context = retrieval_context
        self.n = n

    def measure(self) -> float:
        """
        Compute the ROUGE score between the actual response and the expected response(s).

        Returns:
        float: The computed ROUGE score.
        """
        self.score = self._calculate_scores(
            llm_answer=self.llm_response, context=self.retrieval_context
        )
        return self.score

    def preprocess_text(self, text: str) -> str:
        """
        Preprocess the given text by applying various text preprocessing methods.

        Parameters:
        text (str): The text to preprocess.

        Returns:
        str: The preprocessed text.
        """
        preprocessor = TextPreprocessor()
        preprocessing_methods = [
            preprocessor.to_lower,
            preprocessor.keep_alpha_numeric,
            preprocessor.remove_number,
            preprocessor.remove_stopword,
            preprocessor.lemmatize_word,
        ]
        preprocessed_text = preprocessor.preprocess_text(text, preprocessing_methods)
        return preprocessed_text

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize the given text into a list of words.

        Parameters:
        text (str): The text to tokenize.

        Returns:
        List[str]: The list of tokens.
        """
        return text.split()

    def get_ngrams(self, text: str) -> List[Tuple[str]]:
        """
        Generate n-grams from the given text.

        Parameters:
        text (str): The text to generate n-grams from.

        Returns:
        List[Tuple[str]]: The list of n-grams.
        """
        tokens = self.tokenize(text)
        ngrams = [
            tuple(tokens[i : i + self.n]) for i in range(len(tokens) - self.n + 1)
        ]
        return ngrams

    def count_matches(
        self, llm_answer_ngrams: List[Tuple[str]], context_ngrams: List[Tuple[str]]
    ) -> int:
        """
        Count the number of matching n-grams between the actual response and the expected response.

        Parameters:
        llm_answer_ngrams (List[Tuple[str]]): The n-grams from the language model's response.
        context_ngrams (List[Tuple[str]]): The n-grams from the context text.

        Returns:
        int: The number of matching n-grams.
        """
        llm_answer_counts = Counter(llm_answer_ngrams)
        context_counts = Counter(context_ngrams)
        matches = sum(
            min(context_counts[gram], llm_answer_counts[gram])
            for gram in context_counts
        )
        return matches

    def _calculate_scores(
        self, llm_answer: Union[str, List[str]], context: Union[str, List[str]]
    ) -> Dict[str, float]:
        """
        Calculate the ROUGE scores for the given context(s) and language model response.

        Parameters:
        llm_answer (Union[str, List[str]]): The language model's response.
        context (Union[str, List[str]]): The context text(s).

        Returns:
        Dict[str, float]: A dictionary containing the precision, recall, and F1-score.
        """
        if isinstance(llm_answer, list):
            llm_answer = " ".join(llm_answer)

        if isinstance(context, str):
            context = [context]

        llm_answer = self.preprocess_text(llm_answer)
        processed_contexts = [self.preprocess_text(ctx) for ctx in context]

        llm_answer_ngrams = self.get_ngrams(llm_answer)
        precisions = []
        recalls = []
        f1_scores = []

        for ctx in processed_contexts:
            context_ngrams = self.get_ngrams(ctx)

            matches = self.count_matches(context_ngrams, llm_answer_ngrams)

            precision = (
                matches / len(llm_answer_ngrams) if len(llm_answer_ngrams) > 0 else 0
            )
            recall = matches / len(context_ngrams) if len(context_ngrams) > 0 else 0

            f1_score = (
                2 * (precision * recall) / (precision + recall)
                if (precision + recall) > 0
                else 0
            )

            precisions.append(precision)
            recalls.append(recall)
            f1_scores.append(f1_score)

        average_precision = np.mean(precisions) if precisions else 0
        average_recall = np.mean(recalls) if recalls else 0
        average_f1_score = np.mean(f1_scores) if f1_scores else 0

        scores = {
            "Precision": average_precision,
            "Recall": average_recall,
            "F1-score": average_f1_score,
        }

        return scores
