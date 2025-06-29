from sqlalchemy.orm import Session
from inputimeout import inputimeout, TimeoutOccurred
from src.database import get_db, Script, Feedback, Job

def display_script_summary(script: Script):
    """Displays a summary of the script for feedback."""
    print("\n--- Script for Review ---")
    print(f"Script ID: {script.id}")
    print(f"Idea: {script.job.idea}")
    print(f"Type: {script.script_type}")
    content = str(script.content or '')
    print(f"Excerpt: {content[:250]}...")
    print("-------------------------")

def collect_feedback(db: Session, script: Script) -> str:
    """
    Collects user feedback, saves it to the DB, and updates script/job status.
    Includes a 3-second timeout that defaults to 'approve'.
    """
    action = ""
    try:
        prompt = "Action (approve, revise, quit) [approve]: "
        action = inputimeout(prompt=prompt, timeout=3).lower().strip()
    except TimeoutOccurred:
        action = 'approve'
        print(f"\nTimeout occurred. Defaulting to 'approve' for script {script.id}.")

    if action == 'approve':
        script.status = 'approved'
        new_feedback = Feedback(script_id=script.id, decision='approved')
        db.add(new_feedback)
        
        # Check if all other scripts for this job are also done
        all_scripts = db.query(Script).filter(Script.job_id == script.job_id).all()
        if all(s.status in ['approved', 'revised_and_done'] for s in all_scripts):
            script.job.status = 'approved'
            print(f"Job {script.job.id} approved. Ready for video composition.")

        db.commit()
        print(f"Script {script.id} approved.")
        return 'approved'
        
    elif action == 'revise':
        notes = input("Please provide revision notes: ")
        script.status = 'revision_needed'
        new_feedback = Feedback(script_id=script.id, decision='revised', notes=notes)
        db.add(new_feedback)
        db.commit()
        print("Feedback submitted. The script will be revised.")
        # In a real pipeline, another agent would pick this up.
        return 'revised'
        
    elif action == 'quit':
        return 'quit'
        
    else:
        print("Invalid action. Please choose 'approve', 'revise', or 'quit'.")
        # Recursively call or loop to ensure valid input is eventually received.
        # For simplicity here, we'll just let it end. A robust CLI would loop.
        return 'invalid'

def get_feedback_for_script(db: Session, script_id: int):
    """Retrieves all feedback for a given script."""
    return db.query(Feedback).filter(Feedback.script_id == script_id).all()


def main():
    """Simulates a feedback loop for a script using the database."""
    db: Session = next(get_db())
    
    # Find a pending script to review
    script_to_review = db.query(Script).filter(Script.status == 'pending').first()
    
    if not script_to_review:
        print("No pending scripts to review.")
        # Create one for demonstration if it doesn't exist
        print("Creating a dummy job and script for demonstration...")
        dummy_job = Job(idea="Test Smartwatch", category="Wearables")
        db.add(dummy_job)
        db.commit()
        db.refresh(dummy_job)
        
        script_to_review = Script(
            job_id=dummy_job.id, 
            script_type='long_form', 
            content="This is a test script about a fantastic new smartwatch that definitely needs a review.",
            status='pending'
        )
        db.add(script_to_review)
        db.commit()
        db.refresh(script_to_review)

    display_script_summary(script_to_review)
    result = collect_feedback(db, script_to_review)
    
    if result == 'revised':
        feedback_entries = get_feedback_for_script(db, script_to_review.id)
        print(f"\nLatest revision notes for script {script_to_review.id}: '{feedback_entries[-1].notes}'")
    elif result == 'approved':
        print(f"\nScript {script_to_review.id} approved! Current status: {script_to_review.status}")
        print(f"Job {script_to_review.job.id} status: {script_to_review.job.status}")
    else:
        print("\nExiting feedback loop.")
        
    db.close()

if __name__ == "__main__":
    main() 