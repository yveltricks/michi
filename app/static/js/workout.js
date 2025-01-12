// File: app/static/js/workout.js

// Store workout data
let workoutData = {
    exercises: []
};

// Handle muscle group filtering
document.addEventListener('DOMContentLoaded', function() {
    const muscleFilter = document.getElementById('muscle-filter');
    if (muscleFilter) {
        muscleFilter.addEventListener('change', function() {
            const selectedMuscle = this.value.toLowerCase();
            const exercises = document.querySelectorAll('.exercise-option');
            
            exercises.forEach(exercise => {
                const muscles = exercise.dataset.muscles.toLowerCase();
                if (selectedMuscle === 'all' || muscles.includes(selectedMuscle)) {
                    exercise.style.display = '';
                } else {
                    exercise.style.display = 'none';
                }
            });
        });
    }
});

// Handle adding a new exercise to the workout
function addExercise(exerciseId, exerciseName) {
    const exercise = {
        id: exerciseId,
        name: exerciseName,
        sets: [{ weight: 0, reps: 0 }]
    };
    workoutData.exercises.push(exercise);
    renderExercises();
}

// Handle adding a new set to an exercise
function addSet(exerciseIndex) {
    workoutData.exercises[exerciseIndex].sets.push({ weight: 0, reps: 0 });
    renderExercises();
}

// Handle updating set data
function updateSet(exerciseIndex, setIndex, field, value) {
    if (field === 'weight') {
        // Allow positive decimals for weight
        value = value.replace(/[^0-9.]/g, '');  // Only allow numbers and decimal point
        if (value.split('.').length > 2) {  // Prevent multiple decimal points
            value = value.replace(/\.+$/, '');
        }
        const numValue = parseFloat(value);
        if (!isNaN(numValue) && numValue >= 0) {
            workoutData.exercises[exerciseIndex].sets[setIndex].weight = numValue;
        }
    } else if (field === 'reps') {
        // Only allow positive integers for reps
        const numValue = parseInt(value);
        if (!isNaN(numValue) && numValue > 0) {
            workoutData.exercises[exerciseIndex].sets[setIndex].reps = Math.floor(numValue);
        }
    }
    renderExercises();  // Re-render to show validated values
}

// Handle removing a set
function removeSet(exerciseIndex, setIndex) {
    workoutData.exercises[exerciseIndex].sets.splice(setIndex, 1);
    if (workoutData.exercises[exerciseIndex].sets.length === 0) {
        workoutData.exercises.splice(exerciseIndex, 1);
    }
    renderExercises();
}

// Format sets for display
function formatSets(sets) {
    return `${sets.length} set${sets.length > 1 ? 's' : ''}`;
}

// Render the exercises and their sets
function renderExercises() {
    const container = document.getElementById('exercises-container');
    container.innerHTML = '';
    
    workoutData.exercises.forEach((exercise, exerciseIndex) => {
        const exerciseDiv = document.createElement('div');
        exerciseDiv.className = 'exercise-entry';
        
        let setsHtml = exercise.sets.map((set, setIndex) => `
            <div class="set-entry">
                <span>Set ${setIndex + 1}</span>
                <input type="number" 
                       step="0.1" 
                       min="0" 
                       value="${set.weight}" 
                       onchange="updateSet(${exerciseIndex}, ${setIndex}, 'weight', this.value)" 
                       placeholder="Weight (kg)"
                       class="weight-input">
                <input type="number" 
                       min="1" 
                       step="1" 
                       value="${set.reps}" 
                       onchange="updateSet(${exerciseIndex}, ${setIndex}, 'reps', this.value)" 
                       placeholder="Reps"
                       class="reps-input">
                <button onclick="removeSet(${exerciseIndex}, ${setIndex})" class="remove-set-btn">
                    Remove
                </button>
            </div>
        `).join('');

        exerciseDiv.innerHTML = `
            <h3>${exercise.name} (${formatSets(exercise.sets)})</h3>
            <div class="sets-container">
                ${setsHtml}
            </div>
            <button onclick="addSet(${exerciseIndex})" class="add-set-btn">
                + Add Set
            </button>
        `;
        
        container.appendChild(exerciseDiv);
        
        // Add input event listeners for decimal point fixing
        exerciseDiv.querySelectorAll('.weight-input').forEach(input => {
            input.addEventListener('input', function(e) {
                const cursorPos = this.selectionStart;
                const value = this.value;
                
                // Ensure proper decimal input
                if (value.includes('.')) {
                    const parts = value.split('.');
                    if (parts[0] === '') parts[0] = '0';
                    this.value = parts[0] + '.' + (parts[1] || '');
                    
                    // Restore cursor position after decimal point
                    if (cursorPos > parts[0].length) {
                        this.setSelectionRange(cursorPos, cursorPos);
                    }
                }
            });
        });
    });
}

// Handle exercise modal
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('exercise-modal');
    const btn = document.getElementById('add-exercise-btn');
    const span = document.getElementsByClassName('close')[0];
    const searchInput = document.getElementById('exercise-search');
    const exerciseList = document.getElementById('exercise-list');

    // Open modal
    btn.onclick = function() {
        modal.style.display = 'block';
    }

    // Close modal only when clicking close button
    span.onclick = function() {
        modal.style.display = 'none';
    }

    // Close modal when clicking outside
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    }

    // Handle exercise search
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const exercises = exerciseList.getElementsByClassName('exercise-option');

        Array.from(exercises).forEach(exercise => {
            const name = exercise.getElementsByTagName('h4')[0].textContent.toLowerCase();
            exercise.style.display = name.includes(searchTerm) ? '' : 'none';
        });
    });

    // Handle exercise selection WITHOUT closing modal
    exerciseList.addEventListener('click', function(e) {
        if (e.target.classList.contains('add-btn')) {
            const exerciseDiv = e.target.closest('.exercise-option');
            const exerciseId = exerciseDiv.dataset.id;
            const exerciseName = exerciseDiv.dataset.name;
            
            // Add exercise without closing modal
            addExercise(exerciseId, exerciseName);
            
            // Show feedback
            const addButton = e.target;
            const originalText = addButton.textContent;
            addButton.textContent = 'Added!';
            addButton.style.backgroundColor = '#4CAF50';
            
            setTimeout(() => {
                addButton.textContent = 'Add';
                addButton.style.backgroundColor = '#007bff';
            }, 1000);
        }
    });
});

// Calculate workout duration
function calculateWorkoutDuration() {
    return getWorkoutDuration(); // This uses the actual timer duration
}

// Handle form submission
function completeWorkout() {
    if (workoutData.exercises.length === 0) {
        alert("Please add at least one exercise to your workout.");
        return;
    }

    const title = document.getElementById('workout-title').value.trim() || 'Workout';
    const description = document.getElementById('workout-description').value;
    const rating = document.getElementById('workout-rating').value;

    const data = {
        exercises: workoutData.exercises,
        title: title,
        description: description,
        rating: rating,
        duration: calculateWorkoutDuration()
    };

    fetch('/log-workout', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/';
        } else {
            alert('Error saving workout: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error saving workout');
    });
}