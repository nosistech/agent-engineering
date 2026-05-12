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

DEMO_PATIENT = {
    "patient_id": "P-DEMO",
    "heart_rate_avg": 102.0,
    "spo2_min": 91.5,
    "wbc_count": 14.2,
    "temperature": 38.9,
    "chest_imaging": "right_lower_consolidation",
    "symptoms": ["productive cough", "fever", "shortness of breath"],
}

FEATURE_NAMES = ["heart_rate_avg", "spo2_min", "wbc_count", "temperature"]


def _generate_training_data():
    np.random.seed(42)
    n = 20
    heart_rate = np.random.normal(80, 15, n)
    spo2 = np.random.normal(97, 2, n)
    wbc = np.random.normal(8, 2.5, n)
    temperature = np.random.normal(36.8, 0.5, n)
    X = np.column_stack([heart_rate, spo2, wbc, temperature])
    y = (
        (heart_rate > 100).astype(int)
        + (spo2 < 93).astype(int)
        + (wbc > 11).astype(int)
        + (temperature > 37.8).astype(int)
        >= 1
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

    def make_decision(self, patient: dict) -> dict:
        self.reasoning_trace = []

        features = np.array([[patient[fn] for fn in FEATURE_NAMES]])

        outside = []
        if patient["heart_rate_avg"] > 100:
            outside.append("heart_rate_avg > 100")
        if patient["spo2_min"] < 95:
            outside.append("spo2_min < 95")
        if patient["wbc_count"] > 11:
            outside.append("wbc_count > 11")
        if patient["temperature"] > 37.5:
            outside.append("temperature > 37.5")
        step1 = f"Feature count: {len(FEATURE_NAMES)}"
        if outside:
            step1 += f", outside normal range: {', '.join(outside)}"
        self.reasoning_trace.append({"stage": "Input Analysis", "data": step1})

        proba = self.model.predict_proba(features)[0]
        p_pneumonia = proba[1]
        decision = "pneumonia" if p_pneumonia >= 0.5 else "healthy"
        confidence = float(max(proba))
        self.reasoning_trace.append({
            "stage": "Model Inference",
            "data": f"Raw probability of pneumonia: {p_pneumonia:.4f}",
        })

        if confidence >= 0.75:
            conf_msg = "High confidence"
        elif confidence >= 0.5:
            conf_msg = "Moderate confidence, review recommended"
        else:
            conf_msg = "Low confidence, escalate to human"
        self.reasoning_trace.append({"stage": "Confidence Assessment", "data": conf_msg})

        self.reasoning_trace.append({"stage": "Decision Synthesis", "data": f"Final decision: {decision}"})

        return {
            "decision": decision,
            "confidence": confidence,
            "raw_features": {fn: patient[fn] for fn in FEATURE_NAMES},
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
                            target_class: int = 0) -> dict:
    x = features_array.copy()
    original_pred = model.predict(x)[0]
    if original_pred == target_class:
        return {"changes_required": {}, "feasibility": "Achievable"}

    changes = {}
    for i, name in enumerate(feature_names):
        for direction in [0.9, 1.1]:
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
            return {"level": "Moderate", "action": "Flag for review", "threshold_used": 0.5}
        else:
            return {"level": "Low", "action": "Escalate to human", "threshold_used": 0.5}


def call_llm(prompt: str) -> str:
    response = completion(
        model=MODEL,
        api_base=API_BASE,
        api_key=os.getenv("LITELLM_MASTER_KEY"),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


class DiagnosticAssistant:
    def __init__(self):
        self.agent = ExplainableAgent()
        self.shap = SHAPExplainer()
        self.lime = LIMEExplainer()
        self.confidence_agent = ConfidenceAwareAgent()

    def diagnose(self, patient: dict, audience: str = "clinician") -> dict:
        decision_result = self.agent.make_decision(patient)
        features = np.array([[patient[fn] for fn in FEATURE_NAMES]])

        shap_values = self.shap.explain(
            self.agent.model, features, FEATURE_NAMES,
            baseline_means=self.agent.get_training_mean(),
        )
        lime_values = self.lime.explain(self.agent.model, features, FEATURE_NAMES)
        counterfactual = generate_counterfactual(self.agent.model, features, FEATURE_NAMES, target_class=0)
        confidence_assessment = self.confidence_agent.assess(decision_result["confidence"])

        prompt = f"""You are a medical AI assistant. Generate a {audience} explanation for this diagnostic result.

Patient: {patient['patient_id']}
Decision: {decision_result['decision']}
Confidence: {decision_result['confidence']:.2f}
SHAP Feature Attributions: {shap_values}
LIME Weights: {lime_values}
Counterfactual: {counterfactual}
Confidence Assessment: {confidence_assessment}

For a clinician: include SHAP values, confidence score, and differential reasoning. Use clinical terminology.
For a patient: use plain language only. No numeric scores. Emphasize next steps with their doctor.

Keep the explanation under 150 words."""

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
    assistant = DiagnosticAssistant()

    print("\n=== CLINICIAN REPORT ===")
    clinician_report = assistant.diagnose(DEMO_PATIENT, audience="clinician")
    print(f"Decision: {clinician_report['decision']}")
    print(f"Confidence: {clinician_report['confidence']:.2f}")
    print(f"SHAP Attributions: {clinician_report['shap_values']}")
    print(f"Counterfactual: {clinician_report['counterfactual']}")
    print(f"Explanation:\n{clinician_report['explanation']}")

    print("\n=== PATIENT REPORT ===")
    patient_report = assistant.diagnose(DEMO_PATIENT, audience="patient")
    print(f"Explanation:\n{patient_report['explanation']}")

    print("\n=== REASONING TRACE ===")
    for step in clinician_report["reasoning_trace"]:
        print(f"  {step['stage']}: {step['data']}")