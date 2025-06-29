import sqlite3
from src.config import DB_PATH

def update_script_content():
    """Update script content for testing purposes"""
    script_id = 10
    
    # Sample content for short-form script
    sample_content = """
    Introducing the Portable AR Headset - the ultimate tool for remote engineering and design collaboration.
    
    This lightweight, powerful headset combines high-resolution holographic displays with precision hand tracking.
    
    Engineers can manipulate 3D models in real-time while communicating with team members across the globe.
    
    Built-in spatial mapping creates shared virtual workspaces, enabling multiple users to collaborate on the same project simultaneously.
    
    With 6-hour battery life and industrial-grade durability, it's ready for any worksite.
    
    The Portable AR Headset - transforming how design teams work together, no matter the distance.
    """
    
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Update the script content
        cursor.execute("UPDATE scripts SET content = ? WHERE id = ?", (sample_content, script_id))
        conn.commit()
        
        # Verify the update
        cursor.execute("SELECT content FROM scripts WHERE id = ?", (script_id,))
        updated_content = cursor.fetchone()
        
        conn.close()
        
        if updated_content and updated_content[0]:
            print(f"Successfully updated content for script {script_id}!")
            return True
        else:
            print(f"Failed to update content for script {script_id}.")
            return False
    except Exception as e:
        print(f"Error updating script content: {e}")
        return False

if __name__ == "__main__":
    if update_script_content():
        print("Script content update completed successfully.")
    else:
        print("Script content update failed.") 