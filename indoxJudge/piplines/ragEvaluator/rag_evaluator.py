from loguru import logger
import sys
import json
from indoxJudge.metrics import (
    Faithfulness,
    AnswerRelevancy,
    ContextualRelevancy,
    GEval,
    KnowledgeRetention,
    Hallucination,
    BertScore,
    METEOR,
)
from .graph.ragplot import RagVisualizer

# from ...metrics import Faithfulness
# from ...metrics import AnswerRelevancy
# from ...metrics import ContextualRelevancy
# from ...metrics import GEval
# from ...metrics import Hallucination
# from ...metrics import KnowledgeRetention
# from ...metrics import BertScore
# from ...metrics import METEOR
# Set up logging
logger.remove()  # Remove the default logger
logger.add(
    sys.stdout, format="<green>{level}</green>: <level>{message}</level>", level="INFO"
)
logger.add(
    sys.stdout, format="<red>{level}</red>: <level>{message}</level>", level="ERROR"
)


class RagEvaluator:
    """
    The RagEvaluator class is designed to evaluate various aspects of language model outputs using specified metrics.

    It supports metrics such as Faithfulness, Answer Relevancy, Bias, Contextual Relevancy, GEval, Hallucination,
    Knowledge Retention, Toxicity, BertScore, BLEU, Rouge, and METEOR.
    """

    def __init__(self, llm_as_judge, llm_response, retrieval_context, query):
        """
        Initializes the Evaluator with a language model and a list of metrics.

        Args:
            llm_as_judge: The language model .
        """
        self.model = llm_as_judge
        self.metrics = [
            Faithfulness(
                llm_response=llm_response, retrieval_context=retrieval_context
            ),
            AnswerRelevancy(query=query, llm_response=llm_response),
            ContextualRelevancy(query=query, retrieval_context=retrieval_context),
            GEval(
                parameters="Rag Pipeline",
                llm_response=llm_response,
                query=query,
                retrieval_context=retrieval_context,
            ),
            Hallucination(
                llm_response=llm_response, retrieval_context=retrieval_context
            ),
            KnowledgeRetention(
                messages=[{"query": query, "llm_response": llm_response}]
            ),
            BertScore(llm_response=llm_response, retrieval_context=retrieval_context),
            METEOR(llm_response=llm_response, retrieval_context=retrieval_context),
        ]
        logger.info("Evaluator initialized with model and metrics.")
        self.set_model_for_metrics()
        self.evaluation_score = 0
        self.metrics_score = {}

    def set_model_for_metrics(self):
        """
        Sets the language model for each metric that requires it.
        """
        for metric in self.metrics:
            if hasattr(metric, "set_model"):
                metric.set_model(self.model)
        logger.info("Model set for all metrics.")

    def judge(self):
        """
        Evaluates the language model using the provided metrics and returns the results.

        Returns:
            dict: A dictionary containing the evaluation results for each metric.
        """
        results = {}
        for metric in self.metrics:
            metric_name = metric.__class__.__name__
            try:
                logger.info(f"Evaluating metric: {metric_name}")
                if isinstance(metric, Faithfulness):
                    claims = metric.evaluate_claims()
                    truths = metric.evaluate_truths()
                    verdicts = metric.evaluate_verdicts(claims.claims)
                    reason = metric.evaluate_reason(verdicts, truths.truths)
                    score = metric.calculate_faithfulness_score()
                    results["faithfulness"] = {
                        "claims": claims.claims,
                        "truths": truths.truths,
                        "verdicts": [verdict.__dict__ for verdict in verdicts.verdicts],
                        "score": score,
                        "reason": reason.reason,
                    }
                    self.score["faithfulness"] = score
                elif isinstance(metric, AnswerRelevancy):
                    score = metric.measure()
                    results["answer_relevancy"] = {
                        "score": score,
                        "reason": metric.reason,
                        "statements": metric.statements,
                        "verdicts": [verdict.dict() for verdict in metric.verdicts],
                    }
                    self.score["answer_relevancy"] = score

                elif isinstance(metric, ContextualRelevancy):
                    # Set the language model if not already set
                    irrelevancies = metric.get_irrelevancies(
                        metric.query, metric.retrieval_contexts
                    )
                    metric.set_irrelevancies(irrelevancies)
                    verdicts = metric.get_verdicts(
                        metric.query, metric.retrieval_contexts
                    )
                    # Determine the score, e.g., based on the number of relevant contexts
                    score = (
                        1.0
                        if not irrelevancies
                        else max(
                            0, 1.0 - len(irrelevancies) / len(metric.retrieval_contexts)
                        )
                    )
                    reason = metric.get_reason(irrelevancies, score)
                    results["contextual_relevancy"] = {
                        "verdicts": [verdict.dict() for verdict in verdicts.verdicts],
                        "reason": reason.dict(),
                    }
                    self.score["contextual_relevancy"] = score
                elif isinstance(metric, GEval):

                    geval_result = metric.g_eval()
                    results["geval"] = geval_result.replace("\n", " ")
                    geval_data = json.loads(results["geval"])
                    score = geval_data["score"]
                    self.score["geval"] = int(score) / 8
                elif isinstance(metric, Hallucination):
                    score = metric.measure()
                    results["hallucination"] = {
                        "score": score,
                        "reason": metric.reason,
                        "verdicts": [verdict.dict() for verdict in metric.verdicts],
                    }
                    self.score["hallucination"] = 1 - score
                elif isinstance(metric, KnowledgeRetention):
                    score = metric.measure()
                    results["knowledge_retention"] = {
                        "score": score,
                        "reason": metric.reason,
                        "verdicts": [verdict.dict() for verdict in metric.verdicts],
                        "knowledges": [
                            knowledge.data for knowledge in metric.knowledges
                        ],
                    }
                    self.score["knowledge_retention"] = score

                elif isinstance(metric, BertScore):
                    score = metric.measure()
                    results['BertScore'] = {
                        'precision': score['Precision'],
                        'recall': score['Recall'],
                        'f1_score': score['F1-score']
                    }
                    self.score["BertScore"] = score

                elif isinstance(metric, METEOR):
                    score = metric.measure()
                    results["Meteor"] = {"score": score}

                logger.info(f"Completed evaluation for metric: {metric_name}")
            except Exception as e:
                logger.error(f"Error evaluating metric {metric_name}: {str(e)}")
        return results


# class UniversalRagEvaluator(RagEvaluator):
#     """
#     The UniversalRagEvaluator class evaluates language model outputs using all available metrics.
#     """

#     def __init__(self, model, llm_response, retrieval_context, query):
#         metrics = [
#             Faithfulness(
#                 llm_response=llm_response, retrieval_context=retrieval_context
#             ),
#             AnswerRelevancy(query=query, llm_response=llm_response),
#             ContextualRelevancy(query=query, retrieval_context=retrieval_context),
#             GEval(
#                 parameters="Rag Pipeline",
#                 llm_response=llm_response,
#                 query=query,
#                 retrieval_context=retrieval_context,
#             ),
#             Hallucination(
#                 llm_response=llm_response, retrieval_context=retrieval_context
#             ),
#             KnowledgeRetention(
#                 messages=[{"query": query, "llm_response": llm_response}]
#             ),
#             BertScore(llm_response=llm_response, retrieval_context=retrieval_context),
#             METEOR(llm_response=llm_response, retrieval_context=retrieval_context),
#         ]

#         super().__init__(model, metrics)
#         self.score = {}
#         self.weighted_score, self.weighted_sum = self._calculate_weighted_score(
#             self.score
#         )
    
    def plot(self):
        visualizer = RagVisualizer(metrics=self.metrics_score, score=self.evaluation_score)
        return visualizer.get_dashboard_html()