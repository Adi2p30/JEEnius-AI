#!/usr/bin/env python3
"""
Complete JEE LLM Benchmark Script - All-in-one solution
"""

import json
import time
import os
import sys
import requests
from typing import Dict, List, Optional, Tuple, Any

try:
    import google.generativeai as genai
except ImportError:
    print("Installing Google Generative AI library...")
    os.system(f"{sys.executable} -m pip install google-generativeai")
    import google.generativeai as genai


class LLMBenchmark:
    def __init__(self, questions_file: str, model_name: str, api_key: str):
        self.questions_file = questions_file
        self.model_name = model_name
        self.api_key = api_key
        self.questions = []

        if "gemini" in model_name.lower():
            genai.configure(api_key=api_key)

        self.results = {
            "model": model_name,
            "total_questions": 0,
            "correct_answers": 0,
            "accuracy": 0.0,
            "avg_response_time": 0.0,
            "detailed_results": []
        }

    def load_questions(self) -> None:
        try:
            with open(self.questions_file, 'r') as f:
                self.questions = json.load(f)
            self.results["total_questions"] = len(self.questions)
        except Exception as e:
            print(f"Error loading questions: {e}")
            if not os.path.exists(self.questions_file):
                with open(self.questions_file, 'w') as f:
                    json.dump([], f)
                self.questions = []

    def format_prompt(self, question: Dict[str, Any]) -> str:
        options_text = "\n".join([f"{k}: {v}" for k, v in question["options"].items()])

        prompt = f"""
        Please solve this physics problem from JEE:

        Question: {question["question_text"]}

        Options:
        {options_text}

        Provide your solution step by step and select the correct option (A, B, C, or D).
        """
        return prompt

    def extract_answer(self, response: str) -> str:
        answer_indicators = [
            "the answer is", "answer:", "option", "correct option",
            "correct answer", "selected option", "i select", "i choose"
        ]

        response_lower = response.lower()

        for indicator in answer_indicators:
            if indicator in response_lower:
                pos = response_lower.find(indicator) + len(indicator)
                for i in range(pos, min(pos + 10, len(response))):
                    if response[i] in "ABCD":
                        return response[i]

        positive_indicators = ["correct", "right", "true", "yes", "appropriate", "✓"]

        for option in "ABCD":
            option_pos = response_lower.find(f"option {option.lower()}")
            if option_pos == -1:
                option_pos = response_lower.find(f"{option.lower()})")

            if option_pos != -1:
                snippet = response_lower[option_pos:option_pos + 50]
                for indicator in positive_indicators:
                    if indicator in snippet:
                        return option

        counts = {
            option: response.count(f"Option {option}") + response.count(f"{option})") + response.count(f"{option}.")
            for option in "ABCD"}
        if sum(counts.values()) > 0:
            return max(counts, key=counts.get)

        for char in response:
            if char in "ABCD":
                return char

        return "A"

    def query_model(self, prompt: str) -> Tuple[str, float]:
        try:
            start_time = time.time()

            if "gemini" in self.model_name.lower():
                try:
                    model = genai.GenerativeModel(self.model_name)
                    response = model.generate_content(prompt)
                    response_text = response.text
                except Exception as e:
                    print(f"Gemini API Error: {e}")
                    raise e
            else:
                time.sleep(1)
                response_text = f"After analyzing the problem, I believe the answer is B."

            end_time = time.time()
            response_time = end_time - start_time

            return response_text, response_time

        except Exception as e:
            print(f"Error querying model: {e}")
            return f"Error: {str(e)}", 0.0

    def run_benchmark(self) -> Dict[str, Any]:
        self.load_questions()

        if not self.questions:
            print("No questions loaded. Check your questions file.")
            return self.results

        total_time = 0.0
        correct_count = 0

        for question in self.questions:
            try:
                prompt = self.format_prompt(question)
                response, response_time = self.query_model(prompt)
                total_time += response_time

                extracted_answer = self.extract_answer(response)
                is_correct = extracted_answer == question["selected_answer"]

                if is_correct:
                    correct_count += 1

                self.results["detailed_results"].append({
                    "question_number": question["question_number"],
                    "correct_answer": question["selected_answer"],
                    "model_answer": extracted_answer,
                    "is_correct": is_correct,
                    "response_time": response_time,
                    "model_response": response[:500]
                })

                print(
                    f"Question {question['question_number']}: Model answered {extracted_answer}, correct answer is {question['selected_answer']}")

            except Exception as e:
                print(f"Error processing question {question.get('question_number', 'unknown')}: {e}")
                self.results["detailed_results"].append({
                    "question_number": question.get("question_number", "unknown"),
                    "correct_answer": question.get("selected_answer", "unknown"),
                    "model_answer": "Error",
                    "is_correct": False,
                    "response_time": 0.0,
                    "model_response": f"Error: {str(e)}"
                })

        if self.results["total_questions"] > 0:
            self.results["correct_answers"] = correct_count
            self.results["accuracy"] = correct_count / self.results["total_questions"]
            self.results["avg_response_time"] = total_time / self.results["total_questions"]

        return self.results

    def save_results(self, output_file: str) -> None:
        try:
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"Results saved to {output_file}")
        except Exception as e:
            print(f"Error saving results: {e}")

    def print_summary(self) -> None:
        print("\n" + "=" * 50)
        print(f"Benchmark Summary for {self.model_name}")
        print("=" * 50)
        print(f"Total Questions: {self.results['total_questions']}")
        print(f"Correct Answers: {self.results['correct_answers']}")
        print(f"Accuracy: {self.results['accuracy'] * 100:.2f}%")
        print(f"Average Response Time: {self.results['avg_response_time']:.2f} seconds")
        print("=" * 50)


def create_sample_questions(file_path: str) -> None:
    if os.path.exists(file_path):
        return

    sample_data = [
        {
            "question_number": 1,
            "question_text": "A resistance of $2 Omega$ is connected across one gap of a metre-bridge (the length of the wire is $100 mathrm{~cm}$) and an unknown resistance, greater than $2 Omega$, is connected across the other gap. When these resistances are interchanged, the balance point shifts by $20 mathrm{~cm}$. Neglecting any corrections, the unknown resistance is",
            "options": {
                "A": "3 Omega",
                "B": "4 Omega",
                "C": "5 Omega",
                "D": "6 Omega"
            },
            "selected_answer": "B",
            "page_number": 1
        },
        {
            "question_number": 2,
            "question_text": "In an experiment to determine the focal length $(f)$ of a concave mirror by the $u-v$ method, a student places the object pin $A$ on the principal axis at a distance $x$ from the pole $P$. The student looks at the pin and its inverted image from a distance keeping his/her eye in line with $P$. When the student shifts his/her eye towards left, the image appears to the right of the object pin. Then, (A) $x<f$ (B) $f<x<2f$ (C) $x=2f$ (D) $x>2f$",
            "options": {
                "A": "x<f",
                "B": "f<x<2f",
                "C": "x=2f",
                "D": "x>2f"
            },
            "selected_answer": "B",
            "page_number": 1
        },
        {
            "question_number": 3,
            "question_text": "Two particles of mass $m$ each are tied at the ends of a light string of length $2a$. The whole system is kept on a frictionless horizontal surface with the string held tight so that each mass is at a distance $a$ from the center $P$ (as shown in the figure). Now, the mid-point of the string is pulled vertically upwards with a small but countable force. As the particles move towards each other on the surface. The magnitude of acceleration, when the separation between them becomes $2x$, is",
            "options": {
                "A": "2m g^2 a^{-2}",
                "B": "2m g^2 a^{-2} x",
                "C": "2m g a^{-1}",
                "D": "2m g a^{-1} x"
            },
            "selected_answer": "B",
            "page_number": 1
        }
    ]

    try:
        with open(file_path, 'w') as f:
            json.dump(sample_data, f, indent=2)
        print(f"Created sample questions file: {file_path}")
    except Exception as e:
        print(f"Error creating sample questions file: {e}")


def compare_results(results_list: List[Dict[str, Any]]) -> None:
    if not results_list:
        print("No results to compare.")
        return

    print("\n" + "=" * 70)
    print("MODEL COMPARISON".center(70))
    print("=" * 70)

    print(f"{'Model':<20} | {'Accuracy':<10} | {'Avg Time':<10} | {'Correct':<10}")
    print("-" * 70)

    sorted_results = sorted(results_list, key=lambda x: x["accuracy"], reverse=True)

    for result in sorted_results:
        model = result["model"]
        accuracy = f"{result['accuracy'] * 100:.2f}%"
        avg_time = f"{result['avg_response_time']:.2f}s"
        correct = f"{result['correct_answers']}/{result['total_questions']}"

        print(f"{model:<20} | {accuracy:<10} | {avg_time:<10} | {correct:<10}")

    print("=" * 70)

    if len(results_list) > 0 and results_list[0]["total_questions"] > 0:
        question_count = results_list[0]["total_questions"]

        print("\nPER-QUESTION ANALYSIS")
        print("-" * 70)

        for q_num in range(1, question_count + 1):
            print(f"Question {q_num}:")

            for result in results_list:
                model = result["model"]
                q_detail = next((q for q in result["detailed_results"]
                                 if q["question_number"] == q_num), None)

                if q_detail:
                    model_answer = q_detail["model_answer"]
                    correct_answer = q_detail["correct_answer"]
                    is_correct = q_detail["is_correct"]
                    time = q_detail["response_time"]

                    status = "✓" if is_correct else "✗"
                    print(f"  {model:<20}: {model_answer} ({status}) in {time:.2f}s")
                else:
                    print(f"  {model:<20}: No data")

            print()


def main():
    print("\n" + "=" * 60)
    print("JEE LLM BENCHMARK".center(60))
    print("=" * 60)

    questions_file = "jee_sample.json"
    output_dir = "results"

    gemini_api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyDsYxCXtr-biSn8c5_jynLlG4wJ_msrK4o")

    models = [
        {"name": "gemini-1.5-pro", "api_key": gemini_api_key},
        {"name": "gemini-1.5-flash", "api_key": gemini_api_key},
        {"name": "gemini-2.0-flash", "api_key": gemini_api_key}
    ]

    create_sample_questions(questions_file)

    os.makedirs(output_dir, exist_ok=True)

    genai.configure(api_key=gemini_api_key)
    print(f"Configured Gemini API with provided key")

    all_results = []

    for model_config in models:
        model_name = model_config["name"]
        api_key = model_config["api_key"]

        print(f"\nRunning benchmark for {model_name}...")

        try:
            benchmark = LLMBenchmark(questions_file, model_name, api_key)
            results = benchmark.run_benchmark()

            output_file = os.path.join(output_dir, f"{model_name.replace('/', '-')}_results.json")
            benchmark.save_results(output_file)

            benchmark.print_summary()

            all_results.append(results)

        except Exception as e:
            print(f"Error benchmarking {model_name}: {e}")

    if all_results:
        compare_results(all_results)

        combined_file = os.path.join(output_dir, "combined_results.json")
        try:
            with open(combined_file, 'w') as f:
                json.dump(all_results, f, indent=2)
            print(f"\nCombined results saved to {combined_file}")
        except Exception as e:
            print(f"Error saving combined results: {e}")

    print("\nBenchmark complete!")


if __name__ == "__main__":
    main()