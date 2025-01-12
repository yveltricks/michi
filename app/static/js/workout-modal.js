// File: app/static/js/workout-modal.js

let exerciseModal = {
    isOpen: false,
    searchTerm: '',
    selectedMuscleGroup: 'all',
    exercises: []
};

function toggleExerciseModal() {
    exerciseModal.isOpen = !exerciseModal.isOpen;
    const modal = document.getElementById('exercise-modal');
    modal.style.display = exerciseModal.isOpen ? 'block' : 'none';
}

function filterExercises() {
    const searchInput = document.getElementById('exercise-search').value.toLowerCase();
    const muscleGroup = document.getElementById('muscle-group-filter').value.toLowerCase();
    const exerciseList = document.getElementById('exercise-list');

    exerciseModal.exercises.forEach(exercise => {
        const exerciseElement = document.getElementById(`exercise-${exercise.id}`);
        if (!exerciseElement) return;

        const matchesSearch = exercise.name.toLowerCase().includes(searchInput);
        const matchesMuscle = muscleGroup === 'all' || 
            exercise.muscles_worked.toLowerCase().includes(muscleGroup);

        exerciseElement.style.display = matchesSearch && matchesMuscle ? 'flex' : 'none';
    });
}

function loadExercises() {
    fetch('/api/exercises')
        .then(response => response.json())
        .then(data => {
            exerciseModal.exercises = data;
            renderExerciseList();
        });
}

function renderExerciseList() {
    const exerciseList = document.getElementById('exercise-list');
    exerciseList.innerHTML = exerciseModal.exercises.map(exercise => `
        <div id="exercise-${exercise.id}" class="exercise-option">
            <div class="exercise-info">
                <h4>${exercise.name}</h4>
                <small>${exercise.muscles_worked}</small>
            </div>
            <button onclick="addExerciseAndStayOpen(${exercise.id}, '${exercise.name}')" class="add-btn">
                Add
            </button>
        </div>
    `).join('');
}

function addExerciseAndStayOpen(exerciseId, exerciseName) {
    // Call the original addExercise function
    addExercise(exerciseId, exerciseName);
    
    // Show feedback
    const button = document.querySelector(`#exercise-${exerciseId} .add-btn`);
    const originalText = button.textContent;
    const originalColor = button.style.backgroundColor;
    
    button.textContent = 'Added!';
    button.style.backgroundColor = '#4CAF50';
    
    setTimeout(() => {
        button.textContent = originalText;
        button.style.backgroundColor = originalColor;
    }, 1000);
    
    // Keep modal open
    document.getElementById('exercise-modal').style.display = 'block';
}

document.addEventListener('DOMContentLoaded', () => {
    loadExercises();

    document.getElementById('exercise-search')?.addEventListener('input', filterExercises);
    document.getElementById('muscle-group-filter')?.addEventListener('change', filterExercises);

    // Add CSS for consistent button width
    const style = document.createElement('style');
    style.textContent = `
        .exercise-option {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        .exercise-info {
            flex: 1;
            margin-right: 10px;
        }
        .add-btn {
            min-width: 80px;
            padding: 8px 16px;
            text-align: center;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .add-btn:hover {
            background-color: #0056b3;
        }
    `;
    document.head.appendChild(style);
});