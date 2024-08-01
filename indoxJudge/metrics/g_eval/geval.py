import json

from .template import GEvalTemplate


class GEval:
    def __init__(self, parameters, query, llm_response, retrieval_context, ground_truth=None, context=None):
        """
        Initialize the GEval class with necessary inputs for evaluation.

        Parameters:
        parameters (str): The parameters or aspects to evaluate (e.g., 'summary', 'dialogue').
        query (str): The original query or input text.
        llm_response (str): The response generated by the language model.
        ground_truth (str): The expected or correct output.
        context (str): Additional context relevant to the query.
        retrieval_context (str): The context from which information was retrieved.
        """
        self.model = None
        self.query = query
        self.llm_response = llm_response
        self.ground_truth = ground_truth or ""
        self.context = context or ""
        self.retrieval_context = retrieval_context
        self.parameters = parameters
        self.criteria = """
        1. Retrieval Quality: The retrieved documents or snippets should be relevant and accurate.
        2. Integration: The retrieved information should be well integrated into the generated response.
        3. Coherence: The text should be logically structured and easy to follow.
        4. Relevance: The text should be relevant to the main topic and cover all key points.
        5. Accuracy: The text should be factually accurate and consistent with the source material.
        6. Fluency: The text should be easy to read and free from grammatical errors.
        7. Comprehensiveness: The text should cover all key points and provide a thorough response.
        8. Contextuality: The response should fit well within the context of the query.
        """

    def set_model(self, model):
        """
        Set the model to be used for evaluation.

        Parameters:
        model (str): The model to use.
        """
        self.model = model

    def generate_evaluation_steps(self):
        """
        Generate evaluation steps using the provided parameters and criteria.

        Parameters:
        parameters (str): The parameter to be evaluated (e.g., 'summary', 'dialogue').

        Returns:
        str: The prompt to generate evaluation steps.
        """
        eval_steps_prompt = GEvalTemplate.generate_evaluation_steps(self.parameters, self.criteria)
        return eval_steps_prompt

    def generate_evaluation_results(self, eval_steps):
        """
        Generate evaluation results based on the steps and the provided text.

        Parameters:
        eval_steps (list of str): List of evaluation steps.
        parameters (str): The parameter being evaluated.

        Returns:
        str: The prompt to generate evaluation results.
        """
        eval_results_prompt = GEvalTemplate.generate_evaluation_results(eval_steps, {
            "Query": self.query,
            "LLM response": self.llm_response,
            "Ground truth": self.ground_truth,
            "Context": self.context,
            "Retrieval Context": self.retrieval_context
        }, self.parameters)
        return eval_results_prompt

    def _call_language_model(self, prompt: str) -> str:
        """
        Calls the language model with the given prompt and returns the response.

        Parameters:
        prompt (str): The prompt to provide to the language model.

        Returns:
        str: The response from the language model.
        """
        response = self.model.generate_evaluation_response(prompt=prompt)
        return response

    def g_eval(self):
        """
        Evaluate the quality of natural language generation outputs using the GEvalTemplate.

        This function orchestrates the evaluation process by generating evaluation steps,
        calling the language model to evaluate those steps, and then gathering the evaluation
        results based on the provided query, LLM response, ground truth, and contexts.

        Returns:
        list of dict: Evaluation scores and reasons for each text.
        """
        eval_steps_prompt = self.generate_evaluation_steps()
        eval_steps_response = self._call_language_model(eval_steps_prompt)
        eval_steps = json.loads(eval_steps_response)["steps"]

        eval_results_prompt = self.generate_evaluation_results(eval_steps)
        eval_result = self._call_language_model(eval_results_prompt)

        return eval_result
