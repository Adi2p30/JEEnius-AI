import time
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import threading
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("scraper_log.txt"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class GetMarksScraper:
    def __init__(self, root):
        self.root = root
        self.root.title("GetMarks Questions Scraper")
        self.root.geometry("600x500")
        self.root.resizable(True, True)

        self.driver = None
        self.is_scraping = False
        self.scrape_thread = None

        # Create the UI
        self.create_ui()

    def create_ui(self):
        # Create a main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="GetMarks Questions Scraper", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.pack(fill=tk.X, padx=5, pady=5)

        # URL input
        url_frame = ttk.Frame(config_frame)
        url_frame.pack(fill=tk.X, pady=5)
        ttk.Label(url_frame, text="GetMarks Exam URL:").pack(side=tk.LEFT, padx=5)
        self.url_var = tk.StringVar(value="")
        ttk.Entry(url_frame, textvariable=self.url_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Exam ID input
        exam_id_frame = ttk.Frame(config_frame)
        exam_id_frame.pack(fill=tk.X, pady=5)
        ttk.Label(exam_id_frame, text="Exam ID:").pack(side=tk.LEFT, padx=5)
        self.exam_id_var = tk.StringVar(value="615d76cfc52ffa3c944600e0")
        ttk.Entry(exam_id_frame, textvariable=self.exam_id_var, width=30).pack(side=tk.LEFT, padx=5)

        # Output file input
        output_frame = ttk.Frame(config_frame)
        output_frame.pack(fill=tk.X, pady=5)
        ttk.Label(output_frame, text="Output File:").pack(side=tk.LEFT, padx=5)
        self.output_file_var = tk.StringVar(value="exam_questions.json")
        ttk.Entry(output_frame, textvariable=self.output_file_var, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(output_frame, text="Browse", command=self.browse_output_file).pack(side=tk.LEFT, padx=5)

        # Login frame
        login_frame = ttk.LabelFrame(main_frame, text="Login Information", padding="10")
        login_frame.pack(fill=tk.X, padx=5, pady=5)

        # Username input
        username_frame = ttk.Frame(login_frame)
        username_frame.pack(fill=tk.X, pady=5)
        ttk.Label(username_frame, text="Username/Email:").pack(side=tk.LEFT, padx=5)
        self.username_var = tk.StringVar(value="")
        ttk.Entry(username_frame, textvariable=self.username_var, width=30).pack(side=tk.LEFT, padx=5)

        # Password input
        password_frame = ttk.Frame(login_frame)
        password_frame.pack(fill=tk.X, pady=5)
        ttk.Label(password_frame, text="Password:").pack(side=tk.LEFT, padx=5)
        self.password_var = tk.StringVar(value="")
        ttk.Entry(password_frame, textvariable=self.password_var, width=30, show="*").pack(side=tk.LEFT, padx=5)

        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_var = tk.StringVar(value="Not started")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(fill=tk.X, padx=5, pady=5)

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)

        self.start_button = ttk.Button(button_frame, text="Start Scraping", command=self.start_scraping)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Exit", command=self.exit_app).pack(side=tk.RIGHT, padx=5)

    def update_status(self, message):
        self.status_var.set(message)
        logger.info(message)

    def update_progress(self, current, total):
        if total > 0:
            progress = (current / total) * 100
            self.progress_var.set(progress)

    def browse_output_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.output_file_var.set(filename)

    def start_scraping(self):
        if self.is_scraping:
            messagebox.showinfo("Info", "Scraping is already in progress.")
            return

        # Validate inputs
        url = self.url_var.get()
        username = self.username_var.get()
        password = self.password_var.get()

        if not url:
            messagebox.showerror("Error", "Please enter the GetMarks exam URL.")
            return

        if not (username and password):
            messagebox.showerror("Error", "Please enter your GetMarks login credentials.")
            return

        self.is_scraping = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # Start scraping in a separate thread
        self.scrape_thread = threading.Thread(target=self.run_scraping)
        self.scrape_thread.daemon = True
        self.scrape_thread.start()

    def run_scraping(self):
        try:
            self.update_status("Setting up Chrome browser...")

            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--window-size=1920,1080")

            # Enable headless mode if needed
            # chrome_options.add_argument("--headless")

            # Initialize Chrome driver
            self.update_status("Initializing Chrome driver...")
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )

            # Login to GetMarks
            self.login_to_getmarks()

            # Navigate to exam page
            self.navigate_to_exam()

            # Extract questions
            questions = self.extract_questions_data()

            # Save to JSON file if we have questions
            if questions:
                output_file = self.output_file_var.get()
                exam_id = self.exam_id_var.get()

                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "exam_id": exam_id,
                        "questions": questions
                    }, f, ensure_ascii=False, indent=2)

                self.update_status(f"Successfully saved {len(questions)} questions to {output_file}")
                messagebox.showinfo("Success", f"Successfully saved {len(questions)} questions to {output_file}")
            else:
                self.update_status("No questions were extracted")

        except Exception as e:
            error_msg = f"Error during scraping: {e}"
            logger.error(error_msg)
            self.update_status("Error occurred")
            messagebox.showerror("Error", error_msg)

        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

            self.finish_scraping()

    def login_to_getmarks(self):
        """Log in to GetMarks using the provided credentials"""
        try:
            username = self.username_var.get()
            password = self.password_var.get()

            self.update_status("Logging in to GetMarks...")

            # Navigate to login page
            self.driver.get("https://getmarks.app/login")

            # Wait for the login form to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )

            # Fill in login credentials
            self.driver.find_element(By.ID, "email").send_keys(username)
            self.driver.find_element(By.ID, "password").send_keys(password)

            # Submit the login form
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()

            # Wait for login to complete
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//nav"))
            )

            self.update_status("Successfully logged in to GetMarks")

        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise Exception(f"Failed to log in to GetMarks: {e}")

    def navigate_to_exam(self):
        """Navigate to the exam page"""
        try:
            url = self.url_var.get()

            self.update_status(f"Navigating to exam page: {url}")
            self.driver.get(url)

            # Wait for the page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )

            self.update_status("Successfully loaded exam page")

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            raise Exception(f"Failed to navigate to exam page: {e}")

    def stop_scraping(self):
        if not self.is_scraping:
            return

        self.is_scraping = False
        self.update_status("Stopping scraping... Please wait.")

    def extract_questions_data(self):
        """Extract question data from the current page"""
        try:
            current_url = self.driver.current_url
            self.update_status(f"Extracting data from: {current_url}")

            # Wait for questions to load
            self.update_status("Waiting for questions to load...")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/question/']"))
            )

            # Get all question links
            question_links = []
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/question/']")

            for link in links:
                href = link.get_attribute("href")
                if href and "/question/" in href:
                    question_id = href.split("/")[-1]
                    if not any(q.get("id") == question_id for q in question_links):
                        question_links.append({
                            "id": question_id,
                            "url": href
                        })

            total_questions = len(question_links)
            self.update_status(f"Found {total_questions} questions")

            if total_questions == 0:
                messagebox.showinfo("No Questions", "No questions found on this page.")
                return []

            # Process each question link
            all_questions = []
            for i, question in enumerate(question_links):
                if not self.is_scraping:
                    self.update_status("Scraping stopped by user")
                    break

                current_question = i + 1
                self.update_status(f"Processing question {current_question}/{total_questions}: {question['id']}")
                self.update_progress(current_question, total_questions)

                # Navigate to the question page
                self.driver.get(question["url"])

                # Wait for question content to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ques-text, .question-content"))
                )

                # Extract question data
                try:
                    # Get question text
                    question_text_element = self.driver.find_element(By.CSS_SELECTOR, ".ques-text, .question-content")
                    question_text = question_text_element.get_attribute("innerHTML").strip()

                    # Get options if available
                    options = []
                    try:
                        option_elements = self.driver.find_elements(By.CSS_SELECTOR, ".option-wrapper, .option-item")
                        for opt in option_elements:
                            option_text = opt.get_attribute("innerHTML").strip()
                            is_correct = "correct" in opt.get_attribute("class").lower()
                            options.append({
                                "text": option_text,
                                "isCorrect": is_correct
                            })
                    except Exception as e:
                        logger.warning(f"Error getting options: {e}")

                    # Try to get solution
                    solution_text = ""
                    try:
                        # Click solution button if it exists
                        solution_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Solution')]")
                        solution_btn.click()

                        # Wait for solution to appear
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".solution-text, .solution-content"))
                        )

                        solution_element = self.driver.find_element(By.CSS_SELECTOR,
                                                                    ".solution-text, .solution-content")
                        solution_text = solution_element.get_attribute("innerHTML").strip()
                    except Exception as e:
                        logger.warning(f"Error getting solution: {e}")

                    # Add question data to results
                    question_data = {
                        "_id": question["id"],
                        "question": {
                            "text": question_text
                        },
                        "options": options,
                        "solution": {
                            "text": solution_text
                        }
                    }

                    all_questions.append(question_data)

                except Exception as e:
                    error_msg = f"Error extracting data for question {question['id']}: {e}"
                    logger.error(error_msg)

                # Add a slight delay between questions
                time.sleep(1)

            return all_questions

        except TimeoutException:
            error_msg = "Timed out waiting for questions to load."
            logger.error(error_msg)
            self.update_status("Error: Timed out")
            messagebox.showerror("Timeout Error", error_msg)
            return []

        except Exception as e:
            error_msg = f"Error extracting questions data: {e}"
            logger.error(error_msg)
            self.update_status("Error occurred")
            messagebox.showerror("Error", error_msg)
            return []

    def finish_scraping(self):
        self.is_scraping = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def exit_app(self):
        if self.is_scraping:
            if not messagebox.askyesno("Confirm Exit", "Scraping is in progress. Are you sure you want to exit?"):
                return
            self.is_scraping = False

        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = GetMarksScraper(root)
    root.mainloop()