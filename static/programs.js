// Workout programs built from the equipment clever fit Unterföhring lists: selectorized machines,
// plate-loaded machines, cable stations, power racks, barbells and dumbbells.

// Interchangeable exercises: each group trains the same movement, so any member can be swapped for another.
// [name, equipment]. Names are what gets logged, so keep them stable or history stops matching.
const EXERCISE_GROUPS = [
  [['Bench press', 'Barbell, flat bench'], ['Dumbbell bench press', 'Dumbbells, flat bench'],
   ['Chest press', 'Machine'], ['Plate-loaded chest press', 'Plate-loaded machine'], ['Push-up', 'Bodyweight']],
  [['Incline dumbbell press', 'Dumbbells, incline bench'], ['Incline bench press', 'Barbell, incline bench'],
   ['Incline chest press', 'Plate-loaded machine']],
  [['Pec fly', 'Pec deck machine'], ['Cable fly', 'Cable crossover'], ['Dumbbell fly', 'Dumbbells, flat bench']],
  [['Overhead press', 'Barbell in the power rack'], ['Dumbbell shoulder press', 'Dumbbells, upright bench'],
   ['Shoulder press', 'Machine']],
  [['Dumbbell lateral raise', 'Dumbbells'], ['Cable lateral raise', 'Cable station'], ['Machine lateral raise', 'Machine']],
  [['Face pull', 'Cable station, rope'], ['Rear delt fly', 'Pec deck machine, facing the pad'],
   ['Reverse dumbbell fly', 'Dumbbells, chest on an incline bench']],
  [['Triceps pushdown', 'Cable station, rope or bar'], ['Overhead triceps extension', 'Cable station, rope'],
   ['Skull crusher', 'EZ bar, flat bench'], ['Dip', 'Dip station, or assisted machine']],
  [['Pull-up', 'Pull-up bar, or assisted machine'], ['Lat pulldown', 'Machine'],
   ['Close-grip lat pulldown', 'Machine, close-grip handle']],
  [['Barbell row', 'Barbell'], ['Seated row', 'Machine'], ['Seated cable row', 'Cable station'],
   ['Single-arm dumbbell row', 'Dumbbell, flat bench'], ['Plate-loaded row', 'Plate-loaded machine']],
  [['Barbell curl', 'Barbell or EZ bar'], ['Machine biceps curl', 'Machine'], ['Cable curl', 'Cable station, bar'],
   ['Hammer curl', 'Dumbbells'], ['Incline dumbbell curl', 'Dumbbells, incline bench']],
  [['Back squat', 'Power rack'], ['Leg press', 'Machine'], ['Goblet squat', 'Dumbbell']],
  [['Bulgarian split squat', 'Dumbbells, flat bench'], ['Walking lunge', 'Dumbbells'], ['Step-up', 'Dumbbells, box or bench']],
  [['Deadlift', 'Barbell'], ['Rack pull', 'Barbell in the power rack']],
  [['Romanian deadlift', 'Barbell'], ['Dumbbell Romanian deadlift', 'Dumbbells'], ['Back extension', 'Machine or 45° bench']],
  [['Hip thrust', 'Barbell and bench'], ['Glute bridge', 'Barbell or dumbbell, floor']],
  [['Leg extension', 'Machine']],
  [['Seated leg curl', 'Machine'], ['Lying leg curl', 'Machine']],
  [['Calf raise', 'Calf machine or leg press'], ['Seated calf raise', 'Machine'], ['Dumbbell calf raise', 'Dumbbells, on a step']],
  [['Ab crunch', 'Machine'], ['Cable crunch', 'Cable station, rope'], ['Hanging knee raise', 'Pull-up bar or knee-raise station']],
];
const EXERCISES = {};  // name -> { gear, group }
EXERCISE_GROUPS.forEach(group => group.forEach(([name, gear]) => EXERCISES[name] = { gear, group }));

// Program exercise: [name, sets, reps]. schedule: an object maps weekday (0 = Sunday … 6 = Saturday) to a
// workout; an array is a rolling cycle counted from the program's start date (null = rest day).
// "why" summarizes the research the plan leans on: weekly sets per muscle drive growth (roughly up to
// 10+ sets a week), and with equal weekly sets, training a muscle more often adds little.
const PROGRAMS = [
  {
    id: 'machine-3', type: 'Push/Pull/Legs',
    name: 'Machine PPL, 3 days a week',
    about: 'Beginner. Monday push, Wednesday pull, Friday legs. Machines and cables only.',
    why: 'Each muscle gets about 6 sets a week, once a week. That is below the roughly 10 weekly sets research links to the most growth, but guided machines make it a safe way to learn. Add a fourth set to each exercise once it feels routine.',
    schedule: { 1: 'push', 3: 'pull', 5: 'legs' },
    workouts: {
      push: { name: 'Push', focus: 'Chest, shoulders and triceps', exercises: [
        ['Chest press', 3, '8–12'], ['Shoulder press', 3, '8–12'], ['Pec fly', 3, '10–15'],
        ['Machine lateral raise', 3, '12–15'], ['Triceps pushdown', 3, '10–15'],
      ] },
      pull: { name: 'Pull', focus: 'Back, rear shoulders and biceps', exercises: [
        ['Lat pulldown', 3, '8–12'], ['Seated row', 3, '8–12'], ['Rear delt fly', 3, '12–15'],
        ['Machine biceps curl', 3, '10–12'], ['Back extension', 2, '12–15'],
      ] },
      legs: { name: 'Legs', focus: 'Quads, hamstrings, calves and core', exercises: [
        ['Leg press', 3, '10–12'], ['Leg extension', 3, '12–15'], ['Seated leg curl', 3, '10–12'],
        ['Calf raise', 3, '12–15'], ['Ab crunch', 3, '12–15'],
      ] },
    },
  },
  {
    id: 'classic-6', type: 'Push/Pull/Legs',
    name: 'Classic PPL, 6 days a week',
    about: 'Intermediate. Monday to Saturday. A days are heavy barbell work, B days are higher-rep volume.',
    why: 'Each muscle is trained twice a week for about 12 to 16 sets, which sits in the range research links to the most growth. The cost is six gym visits a week.',
    schedule: { 1: 'pushA', 2: 'pullA', 3: 'legsA', 4: 'pushB', 5: 'pullB', 6: 'legsB' },
    workouts: {
      pushA: { name: 'Push A', focus: 'Heavy chest and shoulders', exercises: [
        ['Bench press', 4, '5–8'], ['Overhead press', 3, '6–8'], ['Incline chest press', 3, '8–10'],
        ['Dumbbell lateral raise', 3, '12–15'], ['Triceps pushdown', 3, '10–12'],
      ] },
      pullA: { name: 'Pull A', focus: 'Heavy back and biceps', exercises: [
        ['Pull-up', 4, '6–10'], ['Barbell row', 4, '6–10'], ['Lat pulldown', 3, '10–12'],
        ['Face pull', 3, '12–15'], ['Barbell curl', 3, '8–12'],
      ] },
      legsA: { name: 'Legs A', focus: 'Heavy squat and hinge', exercises: [
        ['Back squat', 4, '5–8'], ['Romanian deadlift', 3, '8–10'], ['Leg press', 3, '10–12'],
        ['Seated leg curl', 3, '10–12'], ['Calf raise', 4, '10–15'],
      ] },
      pushB: { name: 'Push B', focus: 'Chest and shoulder volume', exercises: [
        ['Incline dumbbell press', 4, '8–12'], ['Chest press', 3, '10–12'], ['Dumbbell shoulder press', 3, '8–12'],
        ['Cable fly', 3, '12–15'], ['Overhead triceps extension', 3, '10–15'],
      ] },
      pullB: { name: 'Pull B', focus: 'Back width and arm volume', exercises: [
        ['Lat pulldown', 4, '8–12'], ['Seated cable row', 3, '10–12'], ['Single-arm dumbbell row', 3, '10–12'],
        ['Rear delt fly', 3, '12–15'], ['Hammer curl', 3, '10–12'],
      ] },
      legsB: { name: 'Legs B', focus: 'Single-leg work and glutes', exercises: [
        ['Bulgarian split squat', 3, '8–12'], ['Leg press', 4, '10–15'], ['Leg extension', 3, '12–15'],
        ['Hip thrust', 3, '8–12'], ['Calf raise', 4, '12–15'],
      ] },
    },
  },
  {
    id: 'rolling-3-1', type: 'Push/Pull/Legs',
    name: 'Rolling PPL, 3 on and 1 off',
    about: 'Intermediate. Push, pull, legs, rest, then repeat, so the weekdays shift. Built around free weights.',
    why: 'Each muscle comes around about 1.75 times a week for roughly 10 to 14 sets. The rest day after every third session helps recovery without a fixed weekly calendar.',
    schedule: ['push', 'pull', 'legs', null],
    workouts: {
      push: { name: 'Push', focus: 'Chest, shoulders and triceps', exercises: [
        ['Bench press', 4, '6–10'], ['Overhead press', 3, '6–10'], ['Incline dumbbell press', 3, '8–12'],
        ['Cable lateral raise', 3, '12–15'], ['Dip', 3, '8–12'], ['Skull crusher', 3, '10–12'],
      ] },
      pull: { name: 'Pull', focus: 'Back, rear shoulders and biceps', exercises: [
        ['Deadlift', 3, '3–5'], ['Pull-up', 3, '6–10'], ['Seated cable row', 3, '10–12'],
        ['Face pull', 3, '12–15'], ['Incline dumbbell curl', 3, '10–12'],
      ] },
      legs: { name: 'Legs', focus: 'Quads, hamstrings, calves and core', exercises: [
        ['Back squat', 4, '6–10'], ['Romanian deadlift', 3, '8–10'], ['Leg press', 3, '12–15'],
        ['Seated leg curl', 3, '10–12'], ['Calf raise', 4, '12–15'], ['Hanging knee raise', 3, '10–15'],
      ] },
    },
  },
  {
    id: 'full-body-3', type: 'Full body',
    name: 'Full body, 3 days a week',
    about: 'Beginner to intermediate. Monday, Wednesday and Friday, three different full-body sessions.',
    why: 'Every muscle is trained three times a week, so you reach about 9 to 12 weekly sets with short sessions. A good pick if you can only go three times a week but want twice-a-week-or-more frequency.',
    schedule: { 1: 'a', 3: 'b', 5: 'c' },
    workouts: {
      a: { name: 'Full body A', focus: 'Squat, bench and row', exercises: [
        ['Back squat', 3, '6–10'], ['Bench press', 3, '6–10'], ['Seated row', 3, '8–12'],
        ['Romanian deadlift', 2, '8–10'], ['Dumbbell lateral raise', 2, '12–15'], ['Ab crunch', 2, '12–15'],
      ] },
      b: { name: 'Full body B', focus: 'Leg press, overhead press and pulldown', exercises: [
        ['Leg press', 3, '10–12'], ['Overhead press', 3, '6–10'], ['Lat pulldown', 3, '8–12'],
        ['Seated leg curl', 3, '10–12'], ['Pec fly', 2, '12–15'], ['Calf raise', 2, '12–15'],
      ] },
      c: { name: 'Full body C', focus: 'Single leg, incline press and pull-up', exercises: [
        ['Bulgarian split squat', 3, '8–12'], ['Incline dumbbell press', 3, '8–12'], ['Pull-up', 3, '6–10'],
        ['Hip thrust', 3, '8–12'], ['Hammer curl', 2, '10–12'], ['Triceps pushdown', 2, '10–15'],
      ] },
    },
  },
  {
    id: 'upper-lower-4', type: 'Upper/lower',
    name: 'Upper/lower, 4 days a week',
    about: 'Intermediate. Monday upper, Tuesday lower, Thursday upper, Friday lower.',
    why: 'Each muscle is trained twice a week for about 10 to 14 sets, matching what the research supports, in four sessions instead of six. A common middle ground between full body and PPL.',
    schedule: { 1: 'upperA', 2: 'lowerA', 4: 'upperB', 5: 'lowerB' },
    workouts: {
      upperA: { name: 'Upper A', focus: 'Heavy press and row', exercises: [
        ['Bench press', 4, '5–8'], ['Barbell row', 4, '6–10'], ['Overhead press', 3, '6–10'],
        ['Lat pulldown', 3, '8–12'], ['Barbell curl', 2, '8–12'], ['Triceps pushdown', 2, '10–12'],
      ] },
      lowerA: { name: 'Lower A', focus: 'Heavy squat and hinge', exercises: [
        ['Back squat', 4, '5–8'], ['Romanian deadlift', 3, '8–10'], ['Leg extension', 3, '12–15'],
        ['Seated leg curl', 3, '10–12'], ['Calf raise', 3, '10–15'],
      ] },
      upperB: { name: 'Upper B', focus: 'Upper-body volume', exercises: [
        ['Incline dumbbell press', 3, '8–12'], ['Seated cable row', 3, '10–12'], ['Dumbbell shoulder press', 3, '8–12'],
        ['Pull-up', 3, '6–10'], ['Cable lateral raise', 3, '12–15'], ['Hammer curl', 2, '10–12'],
        ['Overhead triceps extension', 2, '10–15'],
      ] },
      lowerB: { name: 'Lower B', focus: 'Leg volume and glutes', exercises: [
        ['Leg press', 4, '10–12'], ['Hip thrust', 3, '8–12'], ['Bulgarian split squat', 3, '8–12'],
        ['Lying leg curl', 3, '10–12'], ['Seated calf raise', 3, '12–15'], ['Hanging knee raise', 3, '10–15'],
      ] },
    },
  },
  {
    id: 'body-part-5', type: 'Body-part split',
    name: 'Body-part split, 5 days a week',
    about: 'Intermediate. Chest, back, legs, shoulders and arms on their own days, Monday to Friday.',
    why: 'Each muscle gets 13 to 18 sets in one long session, once a week. With the same weekly sets, research finds frequency matters little, so it works. The trade-off is a full week before a muscle is trained again.',
    schedule: { 1: 'chest', 2: 'back', 3: 'legs', 4: 'shoulders', 5: 'arms' },
    workouts: {
      chest: { name: 'Chest', focus: 'Chest, with some triceps', exercises: [
        ['Bench press', 4, '6–10'], ['Incline dumbbell press', 3, '8–12'], ['Chest press', 3, '10–12'],
        ['Cable fly', 3, '12–15'], ['Dip', 2, '8–12'],
      ] },
      back: { name: 'Back', focus: 'Lats, upper back and lower back', exercises: [
        ['Pull-up', 4, '6–10'], ['Barbell row', 3, '6–10'], ['Lat pulldown', 3, '10–12'],
        ['Seated cable row', 3, '10–12'], ['Back extension', 2, '12–15'],
      ] },
      legs: { name: 'Legs', focus: 'Quads, hamstrings and calves', exercises: [
        ['Back squat', 4, '6–10'], ['Leg press', 3, '10–12'], ['Romanian deadlift', 3, '8–10'],
        ['Leg extension', 3, '12–15'], ['Seated leg curl', 3, '10–12'], ['Calf raise', 4, '10–15'],
      ] },
      shoulders: { name: 'Shoulders', focus: 'Front, side and rear delts', exercises: [
        ['Overhead press', 4, '6–10'], ['Dumbbell lateral raise', 4, '12–15'], ['Shoulder press', 3, '10–12'],
        ['Rear delt fly', 3, '12–15'], ['Face pull', 3, '12–15'],
      ] },
      arms: { name: 'Arms', focus: 'Biceps and triceps', exercises: [
        ['Barbell curl', 3, '8–12'], ['Skull crusher', 3, '10–12'], ['Incline dumbbell curl', 3, '10–12'],
        ['Triceps pushdown', 3, '10–15'], ['Hammer curl', 2, '10–12'], ['Overhead triceps extension', 2, '10–15'],
      ] },
    },
  },
  {
    id: 'strength-5x5', type: 'Strength',
    name: 'Barbell 5×5, every other day',
    about: 'Beginner strength. Two short barbell sessions, A and B, alternating with a rest day between them.',
    why: 'Built for strength rather than size: few exercises, heavy sets of 5. Add 2.5 kg to a lift each time you complete all its reps. Weekly sets per muscle are low, so expect slower muscle growth than the other plans.',
    schedule: ['a', null, 'b', null],
    workouts: {
      a: { name: '5×5 A', focus: 'Squat, bench and row', exercises: [
        ['Back squat', 5, '5'], ['Bench press', 5, '5'], ['Barbell row', 5, '5'],
      ] },
      b: { name: '5×5 B', focus: 'Squat, overhead press and deadlift', exercises: [
        ['Back squat', 5, '5'], ['Overhead press', 5, '5'], ['Deadlift', 1, '5'],
      ] },
    },
  },
];

// self-check: every exercise a program uses needs an entry above, for its equipment and swap options
PROGRAMS.forEach(p => Object.values(p.workouts).forEach(w => w.exercises.forEach(([name]) =>
  console.assert(EXERCISES[name], `programs.js: no EXERCISE_GROUPS entry for "${name}"`))));
