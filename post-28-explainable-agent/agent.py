# MIT License, Copyright 2025 Packt
import os
import logging
import numpy as np
from dotenv import load_dotenv
from sklearn.ensemble import GradientBoostingClassifier
from litellm import completion

load_dotenv()
MODEL = os.getenv("MODEL", "deepseek/deepseek-chat")
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:4000")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DEMO_APPLICATION = {
    "application_id": "APP-DEMO",
    "revenue_growth": 18.5,
    "debt_ratio": 0.72,
    "months_in_business": 14.0,
    "credit_score": 610.0,
}

FEATURE_NAMES = ["revenue_growth", "debt_ratio", "months_in_business", "credit_score"]


def _generate_training_data():
    np.random.seed(42)
    n = 20
    revenue_growth = np.random.normal(15, 10, n)
    debt_ratio = np.random.normal(0.5, 0.2, n)
    months_in_business = np.random.normal(24, 12, n)
    credit_score = np.random.normal(680, 60, n)

    X = np.column_stack([revenue_growth, debt_ratio, months_in_business, credit_score])

    strong_growth = revenue_growth > 20
    low_debt = debt_ratio < 0.4
    established = months_in_business > 18
    good_credit = credit_score > 650

    y = (
        strong_growth.astype(int)
        + low_debt.astype(int)
        + established.astype(int)
        + good_credit.astype(int)
        >= 2
    ).astype(int)

    return X, y


def _train_classifier(X, y):
    model = GradientBoostingClassifier(n_estimators=50, random_state=42)
    model.fit(X, y)
    return model


class ExplainableAgent:
    def __init__(self):
        self.reasoning_trace = []
        self._train_X, self._train_y = _generate_training_data()
        self.model = _train_classifier(self._train_X, self._train_y)
        self.training_mean = np.mean(self._train_X, axis=0)
        logger.info("ExplainableAgent initialized. Classifier trained on synthetic data.")

    def get_training_mean(self):
        return self.training_mean

    def make_decision(self, application: dict) -> dict:
        self.reasoning_trace = []

        features = np.array([[application[fn] for fn in FEATURE_NAMES]])

        flags = []
        if application["revenue_growth"] < 10:
            flags.append("revenue_growth below threshold")
        if application["debt_ratio"] > 0.6:
            flags.append("debt_ratio above threshold")
        if application["months_in_business"] < 18:
            flags.append("months_in_business below threshold")
        if application["credit_score"] < 650:
            flags.append("credit_score below threshold")

        step1 = f"Feature count: {len(FEATURE_NAMES)}"
        if flags:
            step1 += f", risk flags: {', '.join(flags)}"
        self.reasoning_trace.append({"stage": "Input Analysis", "data": step1})

        proba = self.model.predict_proba(features)[0]
        p_approve = proba[1]
        decision = "approve" if p_approve >= 0.5 else "decline"
        confidence = float(max(proba))
        self.reasoning_trace.append({
            "stage": "Model Inference",
            "data": f"Approval probability: {p_approve:.4f}",
        })

        if confidence >= 0.75:
            conf_msg = "High confidence"
        elif confidence >= 0.5:
            conf_msg = "Moderate confidence, analyst review recommended"
        else:
            conf_msg = "Low confidence, escalate to senior analyst"
        self.reasoning_trace.append({"stage": "Confidence Assessment", "data": conf_msg})

        self.reasoning_trace.append({
            "stage": "Decision Synthesis",
            "data": f"Final decision: {decision}",
        })

        return {
            "decision": decision,
            "confidence": confidence,
            "raw_features": {fn: application[fn] for fn in FEATURE_NAMES},
            "reasoning_trace": self.reasoning_trace,
        }


class SHAPExplainer:
    def explain(self, model, features_array: np.ndarray, feature_names: list,
                baseline_means: np.ndarray = None) -> dict:
        if baseline_means is None:
            baseline_means = np.zeros(features_array.shape[1])

        full_pred = model.predict_proba(features_array)[0, 1]
        attributions = {}
        for i, name in enumerate(feature_names):
            masked = features_array.copy()
            masked[0, i] = baseline_means[i]
            masked_pred = model.predict_proba(masked)[0, 1]
            attributions[name] = round(float(full_pred - masked_pred), 4)
        return attributions


class LIMEExplainer:
    def explain(self, model, features_array: np.ndarray, feature_names: list,
                n_samples: int = 50) -> dict:
        np.random.seed(42)
        x0 = features_array[0]
        noise = np.random.normal(0, 0.1, size=(n_samples, len(feature_names)))
        X_pert = x0 + noise
        y_pert = model.predict_proba(X_pert)[:, 1]
        A = np.hstack([np.ones((n_samples, 1)), X_pert])
        coeffs, _, _, _ = np.linalg.lstsq(A, y_pert, rcond=None)
        weights = coeffs[1:]
        return {name: round(float(w), 4) for name, w in zip(feature_names, weights)}


def generate_counterfactual(model, features_array: np.ndarray, feature_names: list,
                            target_class: int = 1) -> dict:
    x = features_array.copy()
    original_pred = model.predict(x)[0]
    if original_pred == target_class:
        return {"changes_required": {}, "feasibility": "Already qualifies"}

    changes = {}
    for i, name in enumerate(feature_names):
        for direction in [1.1, 0.9]:
            candidate = x.copy()
            new_val = candidate[0, i] * direction
            candidate[0, i] = new_val
            if model.predict(candidate)[0] == target_class:
                changes[name] = round(float(new_val), 1)
                break

    feasibility = "Achievable" if 1 <= len(changes) <= 2 else "Complex"
    return {"changes_required": changes, "feasibility": feasibility}


class ConfidenceAwareAgent:
    def assess(self, confidence: float) -> dict:
        if confidence >= 0.75:
            return {"level": "High", "action": "Proceed", "threshold_used": 0.75}
        elif confidence >= 0.5:
            return {"level": "Moderate", "action": "Flag for analyst review", "threshold_used": 0.5}
        else:
            return {"level": "Low", "action": "Escalate to senior analyst", "threshold_used": 0.5}


def call_llm(prompt: str) -> str:
    api_key = os.getenv("LITELLM_API_KEY") or os.getenv("LITELLM_MASTER_KEY")
    if not api_key:
        raise SystemExit(
            "Missing LITELLM_API_KEY. Copy .env.template to .env and fill in the value."
        )

    response = completion(
        model=MODEL,
        api_base=API_BASE,
        api_key=api_key,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


class LoanExplainer:
    def __init__(self):
        self.agent = ExplainableAgent()
        self.shap = SHAPExplainer()
        self.lime = LIMEExplainer()
        self.confidence_agent = ConfidenceAwareAgent()

    def evaluate(self, application: dict, audience: str = "analyst") -> dict:
        decision_result = self.agent.make_decision(application)
        features = np.array([[application[fn] for fn in FEATURE_NAMES]])

        shap_values = self.shap.explain(
            self.agent.model, features, FEATURE_NAMES,
            baseline_means=self.agent.get_training_mean(),
        )
        lime_values = self.lime.explain(self.agent.model, features, FEATURE_NAMES)
        counterfactual = generate_counterfactual(
            self.agent.model, features, FEATURE_NAMES, target_class=1
        )
        confidence_assessment = self.confidence_agent.assess(decision_result["confidence"])

        prompt = f"""You are a loan application summarization assistant. Summarize this application assessment for a {audience}.

Application ID: {application['application_id']}
Decision: {decision_result['decision']}
Confidence: {decision_result['confidence']:.2f}
SHAP Feature Attributions: {shap_values}
LIME Weights: {lime_values}
Counterfactual (what would need to change to qualify): {counterfactual}
Confidence Assessment: {confidence_assessment}

For an analyst: include the SHAP attributions, confidence score, and which risk flags were triggered. Use professional language.
For an applicant: use plain language only. No numeric scores. Explain the outcome and what they could work on improving. Be respectful and constructive.

Important: this is a data summary only. Do not present this as a final lending decision or financial advice. Keep the summary under 150 words."""

        explanation = call_llm(prompt)

        return {
            "decision": decision_result["decision"],
            "confidence": decision_result["confidence"],
            "shap_values": shap_values,
            "lime_values": lime_values,
            "counterfactual": counterfactual,
            "confidence_assessment": confidence_assessment,
            "explanation": explanation.strip(),
            "reasoning_trace": decision_result["reasoning_trace"],
        }


if __name__ == "__main__":
    explainer = LoanExplainer()

    print("\n=== ANALYST REPORT ===")
    analyst_report = explainer.evaluate(DEMO_APPLICATION, audience="analyst")
    print(f"Decision: {analyst_report['decision']}")
    print(f"Confidence: {analyst_report['confidence']:.2f}")
    print(f"SHAP Attributions: {analyst_report['shap_values']}")
    print(f"Counterfactual: {analyst_report['counterfactual']}")
    print(f"Explanation:\n{analyst_report['explanation']}")

    print("\n=== APPLICANT REPORT ===")
    applicant_report = explainer.evaluate(DEMO_APPLICATION, audience="applicant")
    print(f"Explanation:\n{applicant_report['explanation']}")

    print("\n=== REASONING TRACE ===")
    for step in analyst_report["reasoning_trace"]:
        print(f"  {step['stage']}: {step['data']}")
