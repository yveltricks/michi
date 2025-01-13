// File: app/static/js/workout.js

function addExerciseAndStayOpen(exerciseId, exerciseName) {
    // Fetch previous values for this exercise
    fetch(`/api/previous-values/${exerciseId}`)
        .then(response => response.json())
        .then(prevValues => {
            const exercise = {
                id: exerciseId,
                name: exerciseName,
                sets: [{
                    weight: 0,
                    reps: 0,
                    completed: false,
                    set_type: 'normal',
                    prevWeight: prevValues.length > 0 ? prevValues[0].weight : null,
                    prevReps: prevValues.length > 0 ? prevValues[0].reps : null,
                    hasPrevious: prevValues.length > 0
                }]
            };
            workoutData.exercises.push(exercise);
            renderExercises();
        });
}

let currentSetTypeSelection = { exerciseIndex: null, setIndex: null };

const SET_TYPES = {
    normal: { label: '', color: '#000000', displayName: 'Normal' },
    warmup: { label: ' (W)', color: '#FFA500', displayName: 'Warm up' },
    failure: { label: ' (F)', color: '#FF0000', displayName: 'Failure' },
    drop: { label: ' (D)', color: '#800080', displayName: 'Drop' },
    right: { label: ' (R)', color: '#008000', displayName: 'Right' },
    left: { label: ' (L)', color: '#0000FF', displayName: 'Left' },
    negative: { label: ' (N)', color: '#FF4500', displayName: 'Negative' },
    partial: { label: ' (P)', color: '#4B0082', displayName: 'Partial' }
};

function showSetTypeModal(exerciseIndex, setIndex) {
    console.log('Showing modal for:', exerciseIndex, setIndex); // Debug log
    const modal = document.getElementById('set-type-modal');
    const setTypeList = document.getElementById('set-type-list');
    currentSetTypeSelection = { exerciseIndex, setIndex };

    // Clear and populate the set type list
    setTypeList.innerHTML = Object.entries(SET_TYPES).map(([type, info]) => `
        <div class="set-type-option" data-type="${type}">
            <div class="set-type-info">
                <h4 style="color: ${info.color}">${info.displayName}${info.label}</h4>
            </div>
            <button class="select-btn">Select</button>
        </div>
    `).join('');

    // Add click handlers for the options
    setTypeList.querySelectorAll('.set-type-option').forEach(option => {
        const selectBtn = option.querySelector('.select-btn');
        selectBtn.addEventListener('click', () => {
            const newType = option.dataset.type;
            console.log('Selected type:', newType); // Debug log
            workoutData.exercises[exerciseIndex].sets[setIndex].set_type = newType;
            modal.style.display = 'none';
            renderExercises();
        });
    });

    modal.style.display = 'block';
}

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
    // Fetch previous values for this exercise
    fetch(`/api/previous-values/${exerciseId}`)
        .then(response => response.json())
        .then(prevValues => {
            const exercise = {
                id: exerciseId,
                name: exerciseName,
                sets: [{
                    weight: 0,
                    reps: 0,
                    completed: false,
                    set_type: 'normal',
                    prevWeight: prevValues.length > 0 ? prevValues[0].weight : null,
                    prevReps: prevValues.length > 0 ? prevValues[0].reps : null,
                    hasPrevious: prevValues.length > 0
                }]
            };
            workoutData.exercises.push(exercise);
            renderExercises();
        });
}

// Add function to change set type
function changeSetType(exerciseIndex, setIndex, newType) {
    workoutData.exercises[exerciseIndex].sets[setIndex].set_type = newType;
    renderExercises();
}

function loadPreviousValues(exerciseIndex, setIndex) {
    const set = workoutData.exercises[exerciseIndex].sets[setIndex];
    if (set.hasPrevious) {
        set.weight = set.prevWeight;
        set.reps = set.prevReps;
        renderExercises();
    }
}

// Add function to toggle set completion
function toggleSetCompletion(exerciseIndex, setIndex) {
    workoutData.exercises[exerciseIndex].sets[setIndex].completed = 
        !workoutData.exercises[exerciseIndex].sets[setIndex].completed;
    renderExercises();
}

// Handle adding a new set to an exercise
function addSet(exerciseIndex) {
    const lastSet = workoutData.exercises[exerciseIndex].sets[
        workoutData.exercises[exerciseIndex].sets.length - 1
    ];
    
    workoutData.exercises[exerciseIndex].sets.push({
        weight: 0,
        reps: 0,
        completed: false,
        set_type: 'normal',
        previousWeight: lastSet ? lastSet.weight : undefined,
        previousReps: lastSet ? lastSet.reps : undefined
    });
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
    const completedSets = sets.filter(set => set.completed).length;
    return `${completedSets} completed set${completedSets !== 1 ? 's' : ''}`;
}

// Render the exercises and their sets
function renderExercises() {
    const container = document.getElementById('exercises-container');
    container.innerHTML = '';

    workoutData.exercises.forEach((exercise, exerciseIndex) => {
        const exerciseDiv = document.createElement('div');
        exerciseDiv.className = 'exercise-entry';

        let setsHtml = exercise.sets.map((set, setIndex) => {
            const setType = SET_TYPES[set.set_type || 'normal'];
            return `
                <div class="set-entry ${set.completed ? 'checked' : ''}">
                    <span class="set-label" 
                          onclick="showSetTypeModal(${exerciseIndex}, ${setIndex})"
                          style="color: ${setType.color}; cursor: pointer;">
                        Set ${setIndex + 1}${setType.label}
                    </span>
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
                    <label class="set-complete-checkbox">
                        <input type="checkbox"
                            ${set.completed ? 'checked' : ''}
                            onchange="toggleSetCompletion(${exerciseIndex}, ${setIndex})">
                        <span class="checkmark"></span>
                    </label>
                    <button onclick="removeSet(${exerciseIndex}, ${setIndex})" class="remove-set-btn">×</button>
                </div>
            `;
        }).join('');

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
    });
}

// Add this function to show/hide the set type menu
function showSetTypeMenu(exerciseIndex, setIndex) {
    const menuId = `set-type-menu-${exerciseIndex}-${setIndex}`;
    const menu = document.getElementById(menuId);
    
    // Hide all other menus first
    document.querySelectorAll('.set-type-menu').forEach(m => {
        if (m.id !== menuId) {
            m.style.display = 'none';
        }
    });
    
    // Toggle this menu
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}

// Add click event listener to close menus when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.set-type-label')) {
        document.querySelectorAll('.set-type-menu').forEach(menu => {
            menu.style.display = 'none';
        });
    }
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

    // Filter out exercises with no completed sets
    const completedExercises = workoutData.exercises.map(exercise => ({
        ...exercise,
        sets: exercise.sets.filter(set => set.completed)
    })).filter(exercise => exercise.sets.length > 0);

    if (completedExercises.length === 0) {
        alert("Please complete at least one set before finishing the workout.");
        return;
    }

    const data = {
        exercises: completedExercises,
        title: document.getElementById('workout-title').value.trim() || 'Workout',
        description: document.getElementById('workout-description').value,
        rating: document.getElementById('workout-rating').value,
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