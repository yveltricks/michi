# Create this file at "add_title_column.py"
import sqlite3

def migrate():
    # Connect to the database
    conn = sqlite3.connect('app/michi.db')
    cursor = conn.cursor()

    try:
        # Add the title column with a default value
        cursor.execute('ALTER TABLE session ADD COLUMN title TEXT NOT NULL DEFAULT "Workout"')
        
        # Commit the changes
        conn.commit()
        print("Successfully added title column to session table")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Title column already exists")
        else:
            print(f"An error occurred: {e}")
    
    finally:
        # Close the connection
        conn.close()

if __name__ == "__main__":
    migrate()