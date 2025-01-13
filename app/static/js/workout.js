// File: app/static/js/workout.js

// Store workout data
let workoutData = {
    exercises: []
  };
  
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
  
  let currentSetTypeSelection = { exerciseIndex: null, setIndex: null };
  
  function addExerciseAndStayOpen(exerciseId, exerciseName) {
    // Fetch exercise details including input type and previous values
    fetch(`/api/exercise-details/${exerciseId}`)
      .then(response => response.json())
      .then(data => {
        const exercise = {
          id: exerciseId,
          name: exerciseName,
          input_type: data.input_type,
          sets: [{
            completed: false,
            set_type: 'normal',
            ...generateDefaultSetValues(data.input_type),
            prevValues: data.previousValues,
            hasPrevious: data.previousValues !== null
          }]
        };
        workoutData.exercises.push(exercise);
        renderExercises();
      });
  }
  
  function generateDefaultSetValues(inputType) {
    const defaults = {
      'weight_reps': { weight: 0, reps: 0 },
      'bodyweight_reps': { reps: 0 },
      'weighted_bodyweight': { additional_weight: 0, reps: 0 },
      'assisted_bodyweight': { assistance_weight: 0, reps: 0 },
      'duration': { time: 0 },
      'duration_weight': { weight: 0, time: 0 },
      'distance_duration': { distance: 0, time: 0 },
      'weight_distance': { weight: 0, distance: 0 }
    };
    return defaults[inputType] || {};
  }
  
  function formatTime(seconds) {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  
  function renderSetInputs(exercise, exerciseIndex, setIndex, set) {
    const inputFields = [];
    
    switch(exercise.input_type) {
      case 'weight_reps':
        inputFields.push(`
          <input type="number" step="0.1" min="0" value="${set.weight || 0}"
                 onchange="updateSet(${exerciseIndex}, ${setIndex}, 'weight', this.value)"
                 placeholder="Weight (kg)" class="weight-input">
          <input type="number" min="1" step="1" value="${set.reps || 0}"
                 onchange="updateSet(${exerciseIndex}, ${setIndex}, 'reps', this.value)"
                 placeholder="Reps" class="reps-input">`);
        break;
        
      case 'bodyweight_reps':
        inputFields.push(`
          <input type="number" min="1" step="1" value="${set.reps || 0}"
                 onchange="updateSet(${exerciseIndex}, ${setIndex}, 'reps', this.value)"
                 placeholder="Reps" class="reps-input">`);
        break;
        
      case 'weighted_bodyweight':
        inputFields.push(`
          <input type="number" step="0.1" min="0" value="${set.additional_weight || 0}"
                 onchange="updateSet(${exerciseIndex}, ${setIndex}, 'additional_weight', this.value)"
                 placeholder="Added Weight (kg)" class="weight-input">
          <input type="number" min="1" step="1" value="${set.reps || 0}"
                 onchange="updateSet(${exerciseIndex}, ${setIndex}, 'reps', this.value)"
                 placeholder="Reps" class="reps-input">`);
        break;
        
      case 'assisted_bodyweight':
        inputFields.push(`
          <input type="number" step="0.1" min="0" value="${set.assistance_weight || 0}"
                 onchange="updateSet(${exerciseIndex}, ${setIndex}, 'assistance_weight', this.value)"
                 placeholder="Assist Weight (kg)" class="weight-input">
          <input type="number" min="1" step="1" value="${set.reps || 0}"
                 onchange="updateSet(${exerciseIndex}, ${setIndex}, 'reps', this.value)"
                 placeholder="Reps" class="reps-input">`);
        break;
        
      case 'duration':
        inputFields.push(`
          <div class="time-input-container">
            <input type="number" min="0" value="${set.time || 0}"
                   onchange="updateSet(${exerciseIndex}, ${setIndex}, 'time', this.value)"
                   placeholder="Duration (sec)" class="time-input">
            <span class="formatted-time">${formatTime(set.time || 0)}</span>
          </div>`);
        break;
        
      case 'duration_weight':
        inputFields.push(`
          <input type="number" step="0.1" min="0" value="${set.weight || 0}"
                 onchange="updateSet(${exerciseIndex}, ${setIndex}, 'weight', this.value)"
                 placeholder="Weight (kg)" class="weight-input">
          <div class="time-input-container">
            <input type="number" min="0" value="${set.time || 0}"
                   onchange="updateSet(${exerciseIndex}, ${setIndex}, 'time', this.value)"
                   placeholder="Duration (sec)" class="time-input">
            <span class="formatted-time">${formatTime(set.time || 0)}</span>
          </div>`);
        break;
        
      case 'distance_duration':
        inputFields.push(`
          <input type="number" step="0.01" min="0" value="${set.distance || 0}"
                 onchange="updateSet(${exerciseIndex}, ${setIndex}, 'distance', this.value)"
                 placeholder="Distance (km)" class="distance-input">
          <div class="time-input-container">
            <input type="number" min="0" value="${set.time || 0}"
                   onchange="updateSet(${exerciseIndex}, ${setIndex}, 'time', this.value)"
                   placeholder="Duration (sec)" class="time-input">
            <span class="formatted-time">${formatTime(set.time || 0)}</span>
          </div>`);
        break;
        
      case 'weight_distance':
        inputFields.push(`
          <input type="number" step="0.1" min="0" value="${set.weight || 0}"
                 onchange="updateSet(${exerciseIndex}, ${setIndex}, 'weight', this.value)"
                 placeholder="Weight (kg)" class="weight-input">
          <input type="number" step="0.01" min="0" value="${set.distance || 0}"
                 onchange="updateSet(${exerciseIndex}, ${setIndex}, 'distance', this.value)"
                 placeholder="Distance (km)" class="distance-input">`);
        break;
    }
    
    return inputFields.join('');
  }
  
  function updateSet(exerciseIndex, setIndex, field, value) {
    const set = workoutData.exercises[exerciseIndex].sets[setIndex];
    const numValue = parseFloat(value);
    
    if (!isNaN(numValue) && numValue >= 0) {
      set[field] = numValue;
    }
    
    renderExercises();
  }
  
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
  
  function toggleSetCompletion(exerciseIndex, setIndex) {
    workoutData.exercises[exerciseIndex].sets[setIndex].completed = 
        !workoutData.exercises[exerciseIndex].sets[setIndex].completed;
    renderExercises();
  }
  
  function addSet(exerciseIndex) {
    const lastSet = workoutData.exercises[exerciseIndex].sets[
        workoutData.exercises[exerciseIndex].sets.length - 1
    ];
    
    workoutData.exercises[exerciseIndex].sets.push({
        ...generateDefaultSetValues(workoutData.exercises[exerciseIndex].input_type),
        completed: false,
        set_type: 'normal',
        previousWeight: lastSet ? lastSet.weight : undefined,
        previousReps: lastSet ? lastSet.reps : undefined
    });
    renderExercises();
  }
  
  function removeSet(exerciseIndex, setIndex) {
    workoutData.exercises[exerciseIndex].sets.splice(setIndex, 1);
    if (workoutData.exercises[exerciseIndex].sets.length === 0) {
        workoutData.exercises.splice(exerciseIndex, 1);
    }
    renderExercises();
  }
  
  function formatSets(sets) {
    const completedSets = sets.filter(set => set.completed).length;
    return `${completedSets} completed set${completedSets !== 1 ? 's' : ''}`;
  }
  
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
                    ${renderSetInputs(exercise, exerciseIndex, setIndex, set)}
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
  
  // Calculate workout duration
  function calculateWorkoutDuration() {
    return getWorkoutDuration(); // This uses the actual timer duration
  }