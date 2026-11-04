# Scheduling API Documentation

## Phase 5 & 6: Greedy Insertion + ALNS Optimization

This document describes the scheduling API endpoints for executing workforce scheduling algorithms.

---

## Endpoints

### 1. Run Scheduling

**Endpoint:** `POST /api/scheduling/run`

Execute scheduling with Greedy Insertion and/or ALNS optimization.

**Request Body:**
```json
{
  "algorithm": "auto",
  "use_alns": true,
  "job_ids": null,
  "technician_ids": null,
  "max_iterations": 100,
  "destroy_size_min": 5,
  "destroy_size_max": 20,
  "initial_temperature": 100.0,
  "cooling_rate": 0.95,
  "random_seed": 42
}
```

**Parameters:**
- `algorithm`: Algorithm to use
  - `"greedy"` - Greedy Insertion only
  - `"alns"` - ALNS optimization (runs greedy first for initial solution)
  - `"auto"` - Both with comparison (default)
- `use_alns`: Whether to run ALNS after greedy (ignored if algorithm="greedy")
- `job_ids`: List of specific job IDs to schedule, or `null` for all jobs
- `technician_ids`: List of specific technician IDs, or `null` for all
- `max_iterations`: ALNS max iterations (default: 100)
- `destroy_size_min`: ALNS min jobs to destroy (default: 5)
- `destroy_size_max`: ALNS max jobs to destroy (default: 20)
- `initial_temperature`: ALNS initial temperature (default: 100.0)
- `cooling_rate`: ALNS cooling rate (default: 0.95)
- `random_seed`: Random seed for reproducibility (default: 42)

**Response:**
```json
{
  "run_id": 1,
  "status": "completed",
  "algorithm": "auto",
  "jobs_count": 110,
  "technicians_count": 25,
  "assigned_count": 105,
  "unassigned_count": 5,
  "execution_time": 12.45,
  "metrics": {
    "total_score": 8542.30,
    "job_coverage": 95.5,
    "total_travel_time": 1250.0,
    "total_idle_time": 340.0,
    "priority_fulfillment_rate": 98.2,
    "technician_utilization": 87.5
  },
  "assignments": [
    {
      "job_id": 1,
      "technician_id": 5,
      "scheduled_start": "2024-01-15T08:30:00",
      "scheduled_end": "2024-01-15T10:30:00",
      "travel_time_minutes": 15
    }
  ],
  "comparison": {
    "assigned_jobs": {
      "greedy": 102,
      "alns": 105,
      "improvement": 3
    },
    "total_score": {
      "greedy": 8320.50,
      "alns": 8542.30,
      "improvement": 221.80,
      "improvement_pct": 2.67
    },
    "job_coverage": {
      "greedy": 92.7,
      "alns": 95.5,
      "improvement": 2.8
    }
  }
}
```

---

### 2. List Scheduling Runs

**Endpoint:** `GET /api/scheduling/runs?limit=10`

List recent scheduling runs.

**Query Parameters:**
- `limit`: Number of runs to return (1-100, default: 10)

**Response:**
```json
[
  {
    "id": 1,
    "start_time": "2024-01-15T10:30:00",
    "end_time": "2024-01-15T10:30:12",
    "status": "completed",
    "algorithm_used": "auto",
    "total_jobs": 110,
    "jobs_assigned": 105,
    "jobs_unassigned": 5,
    "total_score": 8542.30,
    "execution_time_seconds": 12.45
  }
]
```

---

### 3. Get Scheduling Run Details

**Endpoint:** `GET /api/scheduling/runs/{run_id}`

Get detailed information about a specific scheduling run.

**Response:**
```json
{
  "id": 1,
  "start_time": "2024-01-15T10:30:00",
  "end_time": "2024-01-15T10:30:12",
  "status": "completed",
  "algorithm_used": "auto",
  "total_jobs": 110,
  "total_technicians": 25,
  "jobs_assigned": 105,
  "jobs_unassigned": 5,
  "total_score": 8542.30,
  "total_travel_time": 1250.0,
  "total_idle_time": 340.0,
  "execution_time_seconds": 12.45,
  "assigned_decisions": [
    {
      "job_id": 1,
      "technician_id": 5,
      "scheduled_start": "2024-01-15T08:30:00",
      "scheduled_end": "2024-01-15T10:30:00",
      "algorithm_phase": "alns",
      "priority_score": 100.0
    }
  ],
  "unassigned_decisions": [
    {
      "job_id": 50,
      "algorithm_phase": "alns",
      "rejection_reason": "No eligible technicians with required skills"
    }
  ]
}
```

---

### 4. Delete Scheduling Run

**Endpoint:** `DELETE /api/scheduling/runs/{run_id}`

Delete a scheduling run and its decisions.

**Response:**
```json
{
  "message": "Scheduling run 1 deleted successfully"
}
```

---

### 5. Compare Scheduling Runs

**Endpoint:** `GET /api/scheduling/compare/{run_id_1}/vs/{run_id_2}`

Compare two scheduling runs side by side.

**Response:**
```json
{
  "run_1": {
    "id": 1,
    "algorithm": "greedy",
    "jobs_assigned": 102,
    "total_score": 8320.50,
    "execution_time": 2.15
  },
  "run_2": {
    "id": 2,
    "algorithm": "alns",
    "jobs_assigned": 105,
    "total_score": 8542.30,
    "execution_time": 12.45
  },
  "comparison": {
    "jobs_assigned_delta": 3,
    "score_delta": 221.80,
    "score_improvement_pct": 2.67,
    "execution_time_delta": 10.30
  }
}
```

---

## Algorithm Details

### Phase 5: Greedy Insertion with Least Flexible Job First (LFJ)

**Strategy:**
1. Prioritize jobs by:
   - Priority level (URGENT → HIGH → MEDIUM → LOW)
   - Flexibility (fewer eligible technicians = less flexible)
   - Time window tightness (narrower windows first)
2. For each job, find best insertion position across all eligible technicians
3. Insert based on lowest insertion cost

**Insertion Cost Factors:**
- Travel time to/from job location
- Idle time created in schedule
- Priority weight (higher priority = lower cost preference)
- Time window tightness penalty
- Skill match bonus

### Phase 6: Adaptive Large Neighborhood Search (ALNS)

**Strategy:**
1. Start with greedy solution as initial solution
2. Iteratively destroy and repair parts of solution
3. Accept improvements or worse solutions based on Simulated Annealing
4. Adapt operator weights based on performance

**Destroy Operators:**
- **Random**: Remove random subset of jobs
- **Worst**: Remove jobs with highest insertion costs
- **Related**: Remove jobs in same zone or overlapping time windows
- **Technician**: Remove all jobs from one technician

**Repair Operators:**
- **Greedy**: Insert each job at best position
- **Regret-2**: Prioritize jobs with high regret (large difference between best and 2nd best insertion)
- **Priority**: Insert high-priority jobs first

**Acceptance Criterion:**
- Simulated Annealing with temperature-based acceptance
- Always accept improvements
- Accept worse solutions with probability exp(Δ/T)
- Temperature decreases with cooling rate 0.95

---

## Usage Examples

### Example 1: Run Full Scheduling (Greedy + ALNS)

```bash
curl -X POST "http://localhost:8000/api/scheduling/run" \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "auto",
    "use_alns": true,
    "max_iterations": 100
  }'
```

### Example 2: Run Greedy Only

```bash
curl -X POST "http://localhost:8000/api/scheduling/run" \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "greedy",
    "use_alns": false
  }'
```

### Example 3: Schedule Specific Jobs

```bash
curl -X POST "http://localhost:8000/api/scheduling/run" \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "auto",
    "job_ids": [1, 2, 3, 4, 5],
    "technician_ids": [10, 11, 12]
  }'
```

### Example 4: List Recent Runs

```bash
curl -X GET "http://localhost:8000/api/scheduling/runs?limit=5"
```

### Example 5: Get Run Details

```bash
curl -X GET "http://localhost:8000/api/scheduling/runs/1"
```

---

## Testing

### Run Unit Tests
```bash
cd backend
python test_scheduling.py
```

### Start API Server
```bash
cd backend
python -m uvicorn app.main:app --reload
```

### Access API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Performance Metrics

The scheduling engine tracks comprehensive metrics:

- **Job Coverage**: Percentage of jobs successfully assigned
- **Total Score**: Weighted objective function value (higher is better)
- **Travel Time**: Total travel time across all technicians
- **Idle Time**: Total idle time in technician schedules
- **Priority Fulfillment**: Rate of high-priority jobs assigned
- **Technician Utilization**: Average utilization rate of workforce

---

## Error Handling

The API returns standard HTTP status codes:

- `200 OK`: Successful execution
- `404 Not Found`: Jobs or technicians not found
- `500 Internal Server Error`: Scheduling algorithm failure

All errors include detailed messages in the response body.
