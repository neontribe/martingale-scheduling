from ortools.sat.python import cp_model
import random

# Setup
workers = ['W'+f"{i}" for i in range (0,300)]
tasks = ['T'+f"{j}" for j in range (0,140)]
cost ={}
for ele in workers:
    for ment in tasks:
        cost[(ele, ment)] = random.randint(1,10)

print(cost)
# Index mapping
worker_indices = {w: i for i, w in enumerate(workers)}
task_indices = {t: i for i, t in enumerate(tasks)}

num_workers = len(workers)
num_tasks = len(tasks)

model = cp_model.CpModel()

# Decision variables: x[i][j] = 1 if worker i does task j
x = {}
for w in range(num_workers):
    for t in range(num_tasks):
        x[w, t] = model.NewBoolVar(f'x[{w}][{t}]')

# Each task assigned to exactly one worker
for t in range(num_tasks):
    model.AddExactlyOne(x[w, t] for w in range(num_workers))

# Optional: Each worker does at most one task
for w in range(num_workers):
    model.AddAtMostOne(x[w, t] for t in range(num_tasks))

# Custom Constraint:
# If task A assigned to W1, then task B must be assigned to W2 or W3
# Let x_wa = x[W1][A], x_w2b = x[W2][B], x_w3b = x[W3][B]
# wa = worker_indices['W1']
# ta = task_indices['A']
# tb = task_indices['B']
# w2 = worker_indices['W2']
# w3 = worker_indices['W3']

# # Create an auxiliary bool for "B is assigned to allowed set"
# b_allowed = model.NewBoolVar("b_allowed")
# model.AddBoolOr([x[w2, tb], x[w3, tb]]).OnlyEnforceIf(b_allowed)
# model.AddBoolAnd([x[w2, tb].Not(), x[w3, tb].Not()]).OnlyEnforceIf(b_allowed.Not())

# # Enforce the implication:
# # If x[W1][A] is true → b_allowed must be true
# model.AddImplication(x[wa, ta], b_allowed)

# Objective: minimize total cost
model.Minimize(
    sum(cost[workers[w], tasks[t]] * x[w, t] for w in range(num_workers) for t in range(num_tasks))
)

# Solve
solver = cp_model.CpSolver()
status = solver.Solve(model)

# Output
if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
    for t in range(num_tasks):
        for w in range(num_workers):
            if solver.Value(x[w, t]):
                print(f"Task {tasks[t]} assigned to Worker {workers[w]}")
    print("Total Cost =", solver.ObjectiveValue())
else:
    print("No feasible solution found.")
