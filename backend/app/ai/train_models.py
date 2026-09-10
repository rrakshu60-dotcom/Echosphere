"""
EchoSphere AI Model Training & Evaluation CLI
Trains the local Campus ML models and generates evaluation benchmarks.
"""

import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.echosphere_ml_engine import EchoSphereMLEngine, CampusMLEngine, INTENT_TRAINING_DATA

def main():
    print("=" * 60)
    print("  EchoSphere Campus AI Model Training & Evaluation")
    print("=" * 60)

    engine = CampusMLEngine.get_instance()
    result = engine.train_models()

    print(f" > Status:           {result['status'].upper()}")
    print(f" > Intents Trained:  {result['intents_trained']}")
    print(f" > Training Samples: {result['intent_samples']}")
    print(f" > KB Documents:     {result['kb_documents']}")

    # Validation benchmark tests
    test_queries = [
        ("When is the semester end exam timetable released?", "EXAM_SCHEDULE"),
        ("Are classes cancelled tomorrow because of cyclone rain?", "EMERGENCY_ALERT"),
        ("What companies are coming for placements and what is the CGPA required?", "PLACEMENT_DRIVE"),
        ("Where can I find the CSE department head?", "FACULTY_DEPARTMENT"),
        ("Upcoming college hackathon and coding contest?", "EVENTS_HACKATHONS"),
        ("How do I turn on dark mode in the profile settings?", "APP_NAVIGATION"),
        ("How to create an announcement circular for approval?", "NOTICE_CREATION"),
        ("Explain backpropagation algorithm in machine learning", "BRANCH_STUDIES"),
        ("Tell me a funny joke or riddle", "STUDENT_CHITCHAT_REFUSAL"),
        ("Hello, who are you?", "CONVERSATIONAL"),
    ]

    print("\n" + "-" * 60)
    print("  Benchmark Evaluation on Campus Queries")
    print("-" * 60)

    correct = 0
    for query, expected in test_queries:
        predicted, conf = engine.predict_intent(query)
        is_match = predicted == expected
        if is_match:
            correct += 1
        status_mark = "[PASS]" if is_match else "[FAIL]"
        print(f" {status_mark} '{query[:42]}...'")
        print(f"     Expected: {expected} | Predicted: {predicted} ({conf*100:.1f}%)")

    accuracy = (correct / len(test_queries)) * 100
    print("-" * 60)
    print(f" > Benchmark Accuracy: {accuracy:.1f}% ({correct}/{len(test_queries)})")
    print("=" * 60)

if __name__ == "__main__":
    main()
