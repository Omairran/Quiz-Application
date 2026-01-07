"""
Professional Quiz Application - Semester Project
Supports both Console and GUI modes with complete functionality
"""

import json
import time
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import tkinter as tk
from tkinter import messagebox, ttk
import threading

# ============================================================================
# CORE DATA CLASSES
# ============================================================================

class Question:
    """Represents a single quiz question with all its properties"""
    
    def __init__(self, question: str, options: List[str], correct_answer: int,
                 time_limit: int, marks: int, negative_marks: int):
        self.question = question
        self.options = options
        self.correct_answer = correct_answer
        self.time_limit = time_limit
        self.marks = marks
        self.negative_marks = negative_marks
    
    def is_correct(self, answer: int) -> bool:
        """Check if the given answer is correct"""
        return answer == self.correct_answer
    
    def __repr__(self):
        return f"Question('{self.question[:30]}...', time={self.time_limit}s)"


class QuizResult:
    """Stores the result of a completed quiz"""
    
    def __init__(self, department: str, difficulty: str, score: int, 
                 total_marks: int, percentage: float, player_name: str):
        self.department = department
        self.difficulty = difficulty
        self.score = score
        self.total_marks = total_marks
        self.percentage = percentage
        self.player_name = player_name
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def to_dict(self) -> dict:
        """Convert result to dictionary for JSON storage"""
        return {
            "player_name": self.player_name,
            "score": self.score,
            "total_marks": self.total_marks,
            "percentage": self.percentage,
            "timestamp": self.timestamp
        }
    
    def passed(self) -> bool:
        """Check if the quiz was passed (80% threshold)"""
        return self.percentage >= 80.0


# ============================================================================
# HIGH SCORE MANAGER
# ============================================================================

class HighScoreManager:
    """Manages persistent high scores using JSON file"""
    
    def __init__(self, filename: str = "high_scores.json"):
        self.filename = filename
        self.scores = self._load_scores()
    
    def _load_scores(self) -> dict:
        """Load scores from JSON file or create new structure"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except:
                return self._create_default_structure()
        return self._create_default_structure()
    
    def _create_default_structure(self) -> dict:
        """Create default high score structure"""
        departments = ["Electrical Engineering", "Computer Science", 
                      "Business Administration", "Mathematics"]
        difficulties = ["Easy", "Medium", "Hard", "Expert"]
        
        structure = {}
        for dept in departments:
            structure[dept] = {}
            for diff in difficulties:
                structure[dept][diff] = []
        return structure
    
    def _save_scores(self):
        """Save scores to JSON file"""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.scores, f, indent=2)
        except Exception as e:
            print(f"Error saving high scores: {e}")
    
    def add_score(self, result: QuizResult):
        """Add a new score to the leaderboard"""
        dept_scores = self.scores[result.department][result.difficulty]
        dept_scores.append(result.to_dict())
        
        # Sort by percentage (descending), then by score
        dept_scores.sort(key=lambda x: (-x['percentage'], -x['score']))
        
        # Keep only top 10 scores
        self.scores[result.department][result.difficulty] = dept_scores[:10]
        self._save_scores()
    
    def get_leaderboard(self, department: str, difficulty: str) -> List[dict]:
        """Get leaderboard for specific department and difficulty"""
        return self.scores.get(department, {}).get(difficulty, [])
    
    def get_all_leaderboards(self) -> dict:
        """Get all leaderboards"""
        return self.scores


# ============================================================================
# QUIZ ENGINE
# ============================================================================

class QuizEngine:
    """Core quiz logic shared between Console and GUI modes"""
    
    def __init__(self, questions_file: str = "quiz_questions.json"):
        self.questions_file = questions_file
        self.departments = []
        self.all_questions = {}
        self.current_questions = []
        self.current_question_index = 0
        self.score = 0
        self.total_marks = 0
        self.high_score_manager = HighScoreManager()
        self._load_questions()
    
    def _load_questions(self):
        """Load questions from JSON file"""
        try:
            with open(self.questions_file, 'r') as f:
                data = json.load(f)
                self.all_questions = data['departments']
                self.departments = list(self.all_questions.keys())
        except FileNotFoundError:
            raise FileNotFoundError(f"Questions file '{self.questions_file}' not found!")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in '{self.questions_file}'!")
    
    def get_departments(self) -> List[str]:
        """Get list of available departments"""
        return self.departments
    
    def get_difficulties(self, department: str) -> List[str]:
        """Get available difficulties for a department"""
        return list(self.all_questions.get(department, {}).keys())
    
    def load_quiz(self, department: str, difficulty: str) -> bool:
        """Load a specific quiz"""
        if department not in self.all_questions:
            return False
        if difficulty not in self.all_questions[department]:
            return False
        
        question_data = self.all_questions[department][difficulty]
        self.current_questions = [
            Question(
                q['question'],
                q['options'],
                q['correct_answer'],
                q['time_limit'],
                q['marks'],
                q['negative_marks']
            ) for q in question_data
        ]
        
        self.current_question_index = 0
        self.score = 0
        self.total_marks = sum(q.marks for q in self.current_questions)
        return True
    
    def get_current_question(self) -> Optional[Question]:
        """Get the current question"""
        if 0 <= self.current_question_index < len(self.current_questions):
            return self.current_questions[self.current_question_index]
        return None
    
    def submit_answer(self, answer: Optional[int]) -> Tuple[bool, int, str]:
        """
        Submit an answer and return (is_correct, points_earned, feedback)
        answer can be None if time expired
        """
        question = self.get_current_question()
        if not question:
            return False, 0, "No question available"
        
        if answer is None:
            # Time expired
            points = -question.negative_marks
            self.score += points
            feedback = f"⏰ Time's up! (-{question.negative_marks} marks)"
            return False, points, feedback
        
        if question.is_correct(answer):
            points = question.marks
            self.score += points
            feedback = f"✓ Correct! (+{question.marks} marks)"
            return True, points, feedback
        else:
            points = -question.negative_marks
            self.score += points
            correct_option = question.options[question.correct_answer]
            feedback = f"✗ Wrong! Correct answer: {correct_option} (-{question.negative_marks} marks)"
            return False, points, feedback
    
    def next_question(self) -> bool:
        """Move to next question. Returns True if successful."""
        self.current_question_index += 1
        return self.current_question_index < len(self.current_questions)
    
    def is_quiz_complete(self) -> bool:
        """Check if quiz is complete"""
        return self.current_question_index >= len(self.current_questions)
    
    def get_progress(self) -> Tuple[int, int]:
        """Get current question number and total questions"""
        return (self.current_question_index + 1, len(self.current_questions))
    
    def get_final_result(self, department: str, difficulty: str, 
                         player_name: str) -> QuizResult:
        """Calculate and return final result"""
        percentage = (self.score / self.total_marks * 100) if self.total_marks > 0 else 0
        result = QuizResult(department, difficulty, self.score, 
                           self.total_marks, percentage, player_name)
        self.high_score_manager.add_score(result)
        return result


# ============================================================================
# CONSOLE UI
# ============================================================================

class ConsoleQuizUI:
    """Console-based user interface for the quiz"""
    
    def __init__(self):
        self.engine = QuizEngine()
        self.player_name = ""
        self.current_department = ""
        self.current_difficulty = ""
    
    def clear_screen(self):
        """Clear console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "=" * 70)
        print(f"  {title}".center(70))
        print("=" * 70 + "\n")
    
    def get_input_with_timeout(self, prompt: str, timeout: int) -> Optional[str]:
        """Get user input with timeout (simplified version)"""
        print(f"{prompt} (You have {timeout} seconds)")
        start_time = time.time()
        
        # Note: True timeout implementation requires platform-specific code
        # This is a simplified version for cross-platform compatibility
        user_input = input("Your answer (1-4): ")
        
        elapsed = time.time() - start_time
        if elapsed > timeout:
            return None
        return user_input
    
    def run(self):
        """Main console application loop"""
        self.clear_screen()
        self.print_header("🎓 PROFESSIONAL QUIZ APPLICATION - CONSOLE MODE 🎓")
        
        # Get player name
        self.player_name = input("Enter your name: ").strip()
        if not self.player_name:
            self.player_name = "Anonymous"
        
        while True:
            self.clear_screen()
            self.print_header(f"Welcome, {self.player_name}!")
            
            print("MAIN MENU:")
            print("1. Start Quiz")
            print("2. View Leaderboards")
            print("3. Exit")
            
            choice = input("\nSelect option (1-3): ").strip()
            
            if choice == '1':
                self.start_quiz()
            elif choice == '2':
                self.view_leaderboards()
            elif choice == '3':
                print("\nThank you for using the Quiz Application!")
                break
            else:
                input("\n❌ Invalid choice. Press Enter to continue...")
    
    def start_quiz(self):
        """Quiz selection and execution"""
        # Select department
        self.clear_screen()
        self.print_header("SELECT DEPARTMENT")
        
        departments = self.engine.get_departments()
        for i, dept in enumerate(departments, 1):
            print(f"{i}. {dept}")
        
        dept_choice = input(f"\nSelect department (1-{len(departments)}): ").strip()
        try:
            dept_index = int(dept_choice) - 1
            if 0 <= dept_index < len(departments):
                self.current_department = departments[dept_index]
            else:
                input("\n❌ Invalid selection. Press Enter to continue...")
                return
        except ValueError:
            input("\n❌ Invalid input. Press Enter to continue...")
            return
        
        # Select difficulty
        self.clear_screen()
        self.print_header(f"SELECT DIFFICULTY - {self.current_department}")
        
        difficulties = self.engine.get_difficulties(self.current_department)
        for i, diff in enumerate(difficulties, 1):
            print(f"{i}. {diff}")
        
        diff_choice = input(f"\nSelect difficulty (1-{len(difficulties)}): ").strip()
        try:
            diff_index = int(diff_choice) - 1
            if 0 <= diff_index < len(difficulties):
                self.current_difficulty = difficulties[diff_index]
            else:
                input("\n❌ Invalid selection. Press Enter to continue...")
                return
        except ValueError:
            input("\n❌ Invalid input. Press Enter to continue...")
            return
        
        # Load and run quiz
        if not self.engine.load_quiz(self.current_department, self.current_difficulty):
            input("\n❌ Failed to load quiz. Press Enter to continue...")
            return
        
        self.run_quiz_questions()
    
    def run_quiz_questions(self):
        """Execute the quiz questions"""
        while not self.engine.is_quiz_complete():
            question = self.engine.get_current_question()
            if not question:
                break
            
            self.clear_screen()
            progress = self.engine.get_progress()
            self.print_header(f"Question {progress[0]}/{progress[1]}")
            
            print(f"Department: {self.current_department}")
            print(f"Difficulty: {self.current_difficulty}")
            print(f"Current Score: {self.engine.score}/{self.engine.total_marks}")
            print(f"\nTime Limit: {question.time_limit} seconds")
            print(f"Marks: +{question.marks} | -{question.negative_marks}\n")
            
            print(f"Q: {question.question}\n")
            for i, option in enumerate(question.options, 1):
                print(f"  {i}. {option}")
            
            # Get answer with time tracking
            start_time = time.time()
            user_input = input(f"\nYour answer (1-4, {question.time_limit}s): ").strip()
            elapsed = time.time() - start_time
            
            answer = None
            if elapsed > question.time_limit:
                answer = None  # Time expired
            else:
                try:
                    answer_num = int(user_input)
                    if 1 <= answer_num <= len(question.options):
                        answer = answer_num - 1
                    else:
                        answer = None
                except ValueError:
                    answer = None
            
            # Submit answer and show feedback
            is_correct, points, feedback = self.engine.submit_answer(answer)
            print(f"\n{feedback}")
            print(f"Current Score: {self.engine.score}/{self.engine.total_marks}")
            
            input("\nPress Enter to continue...")
            self.engine.next_question()
        
        # Show final results
        self.show_results()
    
    def show_results(self):
        """Display final quiz results"""
        result = self.engine.get_final_result(
            self.current_department,
            self.current_difficulty,
            self.player_name
        )
        
        self.clear_screen()
        self.print_header("🎯 QUIZ COMPLETED 🎯")
        
        print(f"Player: {result.player_name}")
        print(f"Department: {result.department}")
        print(f"Difficulty: {result.difficulty}")
        print(f"\nFinal Score: {result.score}/{result.total_marks}")
        print(f"Percentage: {result.percentage:.2f}%")
        
        if result.passed():
            print("\n🎉 CONGRATULATIONS! You passed! (80%+ required)")
            print("✓ Next difficulty level unlocked!")
        else:
            print("\n❌ Failed. You need 80% to pass.")
            print("💪 Please retry this level.")
        
        input("\nPress Enter to return to main menu...")
    
    def view_leaderboards(self):
        """Display high scores"""
        self.clear_screen()
        self.print_header("🏆 HIGH SCORES LEADERBOARD 🏆")
        
        all_scores = self.engine.high_score_manager.get_all_leaderboards()
        
        for dept in self.engine.get_departments():
            print(f"\n📚 {dept}")
            print("-" * 70)
            
            for diff in self.engine.get_difficulties(dept):
                scores = all_scores.get(dept, {}).get(diff, [])
                print(f"\n  {diff}:")
                
                if scores:
                    for i, score in enumerate(scores[:5], 1):
                        print(f"    {i}. {score['player_name']}: "
                              f"{score['score']}/{score['total_marks']} "
                              f"({score['percentage']:.1f}%) - "
                              f"{score['timestamp']}")
                else:
                    print("    No scores yet")
        
        input("\nPress Enter to return to main menu...")


# ============================================================================
# GUI MODE
# ============================================================================

class GUIQuizUI:
    """Tkinter-based graphical user interface for the quiz"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Professional Quiz Application")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        self.engine = QuizEngine()
        self.player_name = ""
        self.current_department = ""
        self.current_difficulty = ""
        
        self.timer_running = False
        self.time_remaining = 0
        self.timer_id = None
        
        self.show_welcome_screen()
    
    def clear_window(self):
        """Clear all widgets from window"""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def show_welcome_screen(self):
        """Display welcome screen"""
        self.clear_window()
        
        frame = tk.Frame(self.root, bg='#2c3e50')
        frame.pack(fill='both', expand=True)
        
        tk.Label(frame, text="🎓 Professional Quiz Application", 
                font=('Arial', 24, 'bold'), bg='#2c3e50', fg='white').pack(pady=50)
        
        tk.Label(frame, text="Enter your name:", 
                font=('Arial', 14), bg='#2c3e50', fg='white').pack(pady=10)
        
        name_entry = tk.Entry(frame, font=('Arial', 14), width=30)
        name_entry.pack(pady=10)
        name_entry.focus()
        
        def start():
            name = name_entry.get().strip()
            self.player_name = name if name else "Anonymous"
            self.show_main_menu()
        
        name_entry.bind('<Return>', lambda e: start())
        
        tk.Button(frame, text="START", font=('Arial', 14, 'bold'),
                 bg='#27ae60', fg='white', width=15, height=2,
                 command=start).pack(pady=20)
    
    def show_main_menu(self):
        """Display main menu"""
        self.clear_window()
        
        frame = tk.Frame(self.root, bg='#34495e')
        frame.pack(fill='both', expand=True)
        
        tk.Label(frame, text=f"Welcome, {self.player_name}!", 
                font=('Arial', 20, 'bold'), bg='#34495e', fg='white').pack(pady=40)
        
        tk.Button(frame, text="🎯 Start Quiz", font=('Arial', 16, 'bold'),
                 bg='#3498db', fg='white', width=20, height=2,
                 command=self.show_department_selection).pack(pady=15)
        
        tk.Button(frame, text="🏆 View Leaderboards", font=('Arial', 16, 'bold'),
                 bg='#9b59b6', fg='white', width=20, height=2,
                 command=self.show_leaderboards).pack(pady=15)
        
        tk.Button(frame, text="❌ Exit", font=('Arial', 16, 'bold'),
                 bg='#e74c3c', fg='white', width=20, height=2,
                 command=self.root.quit).pack(pady=15)
    
    def show_department_selection(self):
        """Display department selection screen"""
        self.clear_window()
        
        frame = tk.Frame(self.root, bg='#1abc9c')
        frame.pack(fill='both', expand=True)
        
        tk.Label(frame, text="Select Department", 
                font=('Arial', 22, 'bold'), bg='#1abc9c', fg='white').pack(pady=30)
        
        departments = self.engine.get_departments()
        
        for dept in departments:
            tk.Button(frame, text=dept, font=('Arial', 14),
                     bg='white', fg='#2c3e50', width=30, height=2,
                     command=lambda d=dept: self.select_department(d)).pack(pady=8)
        
        tk.Button(frame, text="← Back", font=('Arial', 12),
                 bg='#95a5a6', fg='white', width=15,
                 command=self.show_main_menu).pack(pady=20)
    
    def select_department(self, department: str):
        """Handle department selection"""
        self.current_department = department
        self.show_difficulty_selection()
    
    def show_difficulty_selection(self):
        """Display difficulty selection screen"""
        self.clear_window()
        
        frame = tk.Frame(self.root, bg='#e67e22')
        frame.pack(fill='both', expand=True)
        
        tk.Label(frame, text=f"Select Difficulty\n{self.current_department}", 
                font=('Arial', 20, 'bold'), bg='#e67e22', fg='white').pack(pady=30)
        
        difficulties = self.engine.get_difficulties(self.current_department)
        colors = {
            'Easy': '#27ae60',
            'Medium': '#f39c12',
            'Hard': '#e74c3c',
            'Expert': '#8e44ad'
        }
        
        for diff in difficulties:
            color = colors.get(diff, '#3498db')
            tk.Button(frame, text=diff, font=('Arial', 14, 'bold'),
                     bg=color, fg='white', width=25, height=2,
                     command=lambda d=diff: self.select_difficulty(d)).pack(pady=10)
        
        tk.Button(frame, text="← Back", font=('Arial', 12),
                 bg='#95a5a6', fg='white', width=15,
                 command=self.show_department_selection).pack(pady=20)
    
    def select_difficulty(self, difficulty: str):
        """Handle difficulty selection and start quiz"""
        self.current_difficulty = difficulty
        
        if self.engine.load_quiz(self.current_department, self.current_difficulty):
            self.show_quiz_question()
        else:
            messagebox.showerror("Error", "Failed to load quiz!")
            self.show_main_menu()
    
    def show_quiz_question(self):
        """Display current quiz question"""
        if self.engine.is_quiz_complete():
            self.show_results()
            return
        
        question = self.engine.get_current_question()
        if not question:
            self.show_results()
            return
        
        self.clear_window()
        self.stop_timer()
        
        frame = tk.Frame(self.root, bg='#ecf0f1')
        frame.pack(fill='both', expand=True)
        
        # Header
        progress = self.engine.get_progress()
        header_frame = tk.Frame(frame, bg='#2c3e50')
        header_frame.pack(fill='x')
        
        tk.Label(header_frame, text=f"Question {progress[0]}/{progress[1]}", 
                font=('Arial', 16, 'bold'), bg='#2c3e50', fg='white').pack(side='left', padx=20, pady=10)
        
        tk.Label(header_frame, text=f"Score: {self.engine.score}/{self.engine.total_marks}", 
                font=('Arial', 14), bg='#2c3e50', fg='#27ae60').pack(side='right', padx=20)
        
        # Timer
        timer_frame = tk.Frame(frame, bg='#e74c3c')
        timer_frame.pack(fill='x')
        
        self.timer_label = tk.Label(timer_frame, text=f"⏱ Time: {question.time_limit}s", 
                                    font=('Arial', 14, 'bold'), bg='#e74c3c', fg='white')
        self.timer_label.pack(pady=5)
        
        # Question info
        info_frame = tk.Frame(frame, bg='#ecf0f1')
        info_frame.pack(pady=10)
        
        tk.Label(info_frame, text=f"{self.current_department} - {self.current_difficulty}", 
                font=('Arial', 12), bg='#ecf0f1', fg='#7f8c8d').pack()
        
        tk.Label(info_frame, text=f"Marks: +{question.marks} | Penalty: -{question.negative_marks}", 
                font=('Arial', 11), bg='#ecf0f1', fg='#e67e22').pack()
        
        # Question text
        question_frame = tk.Frame(frame, bg='white', relief='solid', borderwidth=1)
        question_frame.pack(pady=15, padx=30, fill='x')
        
        tk.Label(question_frame, text=question.question, 
                font=('Arial', 14), bg='white', wraplength=700, justify='left').pack(pady=20, padx=20)
        
        # Options
        self.selected_option = tk.IntVar(value=-1)
        
        for i, option in enumerate(question.options):
            rb = tk.Radiobutton(frame, text=f"{chr(65+i)}. {option}", 
                               variable=self.selected_option, value=i,
                               font=('Arial', 12), bg='#ecf0f1', 
                               activebackground='#bdc3c7',
                               selectcolor='#3498db',
                               wraplength=700, justify='left')
            rb.pack(anchor='w', padx=50, pady=8)
        
        # Submit button
        tk.Button(frame, text="Submit Answer", font=('Arial', 14, 'bold'),
                 bg='#27ae60', fg='white', width=20, height=2,
                 command=self.submit_current_answer).pack(pady=20)
        
        # Start timer
        self.time_remaining = question.time_limit
        self.start_timer()
    
    def start_timer(self):
        """Start countdown timer"""
        self.timer_running = True
        self.update_timer()
    
    def stop_timer(self):
        """Stop countdown timer"""
        self.timer_running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
    
    def update_timer(self):
        """Update timer display"""
        if not self.timer_running:
            return
        
        if self.time_remaining > 0:
            self.timer_label.config(text=f"⏱ Time: {self.time_remaining}s")
            self.time_remaining -= 1
            self.timer_id = self.root.after(1000, self.update_timer)
        else:
            self.timer_label.config(text="⏱ Time: 0s - TIME'S UP!")
            self.stop_timer()
            self.root.after(500, lambda: self.submit_current_answer(timeout=True))
    
    def submit_current_answer(self, timeout=False):
        """Submit answer and show feedback"""
        self.stop_timer()
        
        answer = None if timeout else (self.selected_option.get() if self.selected_option.get() >= 0 else None)
        
        is_correct, points, feedback = self.engine.submit_answer(answer)
        
        # Show feedback
        if is_correct:
            messagebox.showinfo("Result", feedback)
        else:
            messagebox.showwarning("Result", feedback)
        
        # Move to next question
        self.engine.next_question()
        self.show_quiz_question()
    
    def show_results(self):
        """Display final results"""
        result = self.engine.get_final_result(
            self.current_department,
            self.current_difficulty,
            self.player_name
        )
        
        self.clear_window()
        
        bg_color = '#27ae60' if result.passed() else '#e74c3c'
        frame = tk.Frame(self.root, bg=bg_color)
        frame.pack(fill='both', expand=True)
        
        status = "🎉 PASSED!" if result.passed() else "❌ FAILED"
        tk.Label(frame, text=status, 
                font=('Arial', 28, 'bold'), bg=bg_color, fg='white').pack(pady=30)
        
        info_text = f"""
Player: {result.player_name}
Department: {result.department}
Difficulty: {result.difficulty}

Final Score: {result.score}/{result.total_marks}
Percentage: {result.percentage:.2f}%

{"✓ Next level unlocked!" if result.passed() else "💪 Please retry (need 80%)"}
        """
        
        tk.Label(frame, text=info_text, 
                font=('Arial', 14), bg=bg_color, fg='white',
                justify='center').pack(pady=20)
        
        tk.Button(frame, text="Return to Main Menu", font=('Arial', 14, 'bold'),
                 bg='white', fg=bg_color, width=20, height=2,
                 command=self.show_main_menu).pack(pady=20)
    
    def show_leaderboards(self):
        """Display leaderboards"""
        self.clear_window()
        
        frame = tk.Frame(self.root, bg='#34495e')
        frame.pack(fill='both', expand=True)
        
        tk.Label(frame, text="🏆 High Scores Leaderboard", 
                font=('Arial', 20, 'bold'), bg='#34495e', fg='white').pack(pady=20)
        
        # Create scrollable frame
        canvas = tk.Canvas(frame, bg='#34495e', highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#34495e')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Display all leaderboards
        all_scores = self.engine.high_score_manager.get_all_leaderboards()
        
        for dept in self.engine.get_departments():
            dept_frame = tk.Frame(scrollable_frame, bg='#2c3e50', relief='ridge', borderwidth=2)
            dept_frame.pack(padx=20, pady=10, fill='x')
            
            tk.Label(dept_frame, text=f"📚 {dept}", 
                    font=('Arial', 14, 'bold'), bg='#2c3e50', fg='#ecf0f1').pack(pady=5)
            
            for diff in self.engine.get_difficulties(dept):
                diff_frame = tk.Frame(dept_frame, bg='#34495e', relief='sunken', borderwidth=1)
                diff_frame.pack(padx=10, pady=5, fill='x')
                
                tk.Label(diff_frame, text=f"{diff}:", 
                        font=('Arial', 11, 'bold'), bg='#34495e', fg='#f39c12').pack(anchor='w', padx=5)
                
                scores = all_scores.get(dept, {}).get(diff, [])
                
                if scores:
                    for i, score in enumerate(scores[:3], 1):
                        score_text = (f"{i}. {score['player_name']}: "
                                    f"{score['score']}/{score['total_marks']} "
                                    f"({score['percentage']:.1f}%)")
                        tk.Label(diff_frame, text=score_text, 
                                font=('Arial', 9), bg='#34495e', fg='#bdc3c7').pack(anchor='w', padx=15)
                else:
                    tk.Label(diff_frame, text="No scores yet", 
                            font=('Arial', 9, 'italic'), bg='#34495e', fg='#7f8c8d').pack(anchor='w', padx=15)
        
        canvas.pack(side='left', fill='both', expand=True, padx=10)
        scrollbar.pack(side='right', fill='y')
        
        tk.Button(frame, text="← Back to Menu", font=('Arial', 12),
                 bg='#95a5a6', fg='white', width=15,
                 command=self.show_main_menu).pack(pady=10)


# ============================================================================
# STARTUP MODE SELECTION
# ============================================================================

def show_mode_selection():
    """Display startup menu to choose between Console and GUI mode"""
    print("\n" + "=" * 70)
    print("  🎓 PROFESSIONAL QUIZ APPLICATION 🎓".center(70))
    print("=" * 70)
    print("\nSELECT MODE:")
    print("1. Console-Based Quiz (Terminal)")
    print("2. GUI-Based Quiz (Tkinter Window)")
    print("3. Exit")
    print("-" * 70)
    
    while True:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            return 'console'
        elif choice == '2':
            return 'gui'
        elif choice == '3':
            print("\nThank you! Goodbye!")
            return None
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")


def main():
    """Main entry point of the application"""
    try:
        # Check if required files exist
        if not os.path.exists("quiz_questions.json"):
            print("\n❌ ERROR: 'quiz_questions.json' not found!")
            print("Please ensure the questions file is in the same directory.")
            input("\nPress Enter to exit...")
            return
        
        # Show mode selection
        mode = show_mode_selection()
        
        if mode == 'console':
            # Run console mode
            console_ui = ConsoleQuizUI()
            console_ui.run()
            
        elif mode == 'gui':
            # Run GUI mode
            root = tk.Tk()
            app = GUIQuizUI(root)
            root.mainloop()
    
    except KeyboardInterrupt:
        print("\n\nApplication interrupted by user.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()