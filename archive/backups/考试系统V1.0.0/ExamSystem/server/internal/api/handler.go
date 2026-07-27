package api

import (
    "encoding/json"
    "net/http"
    "strconv"

    "examsystem/internal/config"
	"examsystem/internal/engine"
    "examsystem/internal/logger"
    "examsystem/model"
    "examsystem/internal/storage"
)

type RecordResponse struct {
    ID          int               `json:"id"`
    Text        string            `json:"text"`
    Options     map[string]string `json:"options"`
    Answer      string            `json:"answer"`
    Score       int               `json:"score"`
    Chosen      string            `json:"chosen"`
    IsCorrect   bool              `json:"is_correct"`
    EarnedScore int               `json:"earned_score"`
}

type SubmitResponse struct {
    TotalScore   int              `json:"total_score"`
    EarnedScore  int              `json:"earned_score"`
    CorrectCount int              `json:"correct_count"`
    TotalCount   int              `json:"total_count"`
    Records      []RecordResponse `json:"records"`
}

type QuestionResponse struct {
    ID      int               `json:"id"`
    Text    string            `json:"text"`
    Options map[string]string `json:"options"`
    Score   int               `json:"score"`
}

type Handler struct {
    Engine          *engine.Engine
    Storage         *storage.Storage
    SessionManager  *engine.SessionManager
    Config          *config.Config
}

func NewHandler(eng *engine.Engine, stg *storage.Storage, sm *engine.SessionManager, cfg *config.Config) *Handler {
    return &Handler{Engine: eng, Storage: stg, SessionManager: sm, Config: cfg}
}

func (h *Handler) RegisterRoutes(mux *http.ServeMux) {
    mux.HandleFunc("GET /health", h.healthCheck)
    mux.HandleFunc("GET /questions", h.auth(h.handleQuestions))
    mux.HandleFunc("POST /submit", h.auth(h.handleSubmit))
    mux.HandleFunc("POST /answer", h.auth(h.handleAnswer))
    mux.HandleFunc("POST /start", h.auth(h.handleStart))
    mux.HandleFunc("POST /load_questions", h.auth(h.handleLoadQuestions))
}

func (h *Handler) healthCheck(w http.ResponseWriter, r *http.Request) {
    logger.Info.Println("Health check called")
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func (h *Handler) handleQuestions(w http.ResponseWriter, r *http.Request) {
    questions := h.Engine.Questions
    resp := make([]QuestionResponse, len(questions))
    for i, q := range questions {
        resp[i] = QuestionResponse{
            ID:      q.ID,
            Text:    q.Text,
            Options: q.Options,
            Score:   q.Score,
        }
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(resp)
}

func (h *Handler) handleSubmit(w http.ResponseWriter, r *http.Request) {
    var result engine.ExamResult
    if sessionID := r.URL.Query().Get("session_id"); sessionID != "" {
        res, err := h.SessionManager.SubmitSession(sessionID)
        if err != nil {
            http.Error(w, err.Error(), http.StatusNotFound)
            return
        }
        if res == nil {
            http.Error(w, "session not found", http.StatusNotFound)
            return
        }
        result = *res
    } else {
        var raw map[string]string
        if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
            http.Error(w, "Invalid JSON", http.StatusBadRequest)
            return
        }
        sess := h.Engine.CreateSession()
        for qidStr, choice := range raw {
            qid, err := strconv.Atoi(qidStr)
            if err != nil {
                continue
            }
            if err := sess.Answer(qid, choice); err != nil {
                http.Error(w, err.Error(), http.StatusBadRequest)
                return
            }
        }
        result = sess.Submit()
    }

    var records []RecordResponse
    for i := range result.Records {
        rec := &result.Records[i]
        records = append(records, RecordResponse{
            ID:          rec.Question.ID,
            Text:        rec.Question.Text,
            Options:     rec.Question.Options,
            Answer: func() string {
                if h.Config.Exam.ShowAnswerAfterSubmit {
                    return rec.Question.Answer
                }
                return ""
            }(),
            Score:       rec.Question.Score,
            Chosen:      rec.Chosen,
            IsCorrect:   rec.IsCorrect,
            EarnedScore: rec.EarnedScore,
        })
    }

    resp := SubmitResponse{
        TotalScore:   result.TotalScore,
        EarnedScore:  result.EarnedScore,
        CorrectCount: result.CorrectCount,
        TotalCount:   result.TotalCount,
        Records:      records,
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(resp)
}

func (h *Handler) handleAnswer(w http.ResponseWriter, r *http.Request) {
    var body struct {
        SessionID string `json:"session_id"`
        QID    int    `json:"qid"`
        Choice string `json:"choice"`
    }
    if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
        http.Error(w, "Invalid JSON", http.StatusBadRequest)
        return
    }
    if body.SessionID != "" {
        if err := h.SessionManager.SaveAnswer(body.SessionID, body.QID, body.Choice); err != nil {
            http.Error(w, err.Error(), http.StatusBadRequest)
            return
        }
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]bool{"ok": true})
}

func (h *Handler) handleStart(w http.ResponseWriter, r *http.Request) {
    if len(h.Engine.Questions) == 0 {
        http.Error(w, "No questions loaded", http.StatusBadRequest)
        return
    }
    _, sessionID := h.SessionManager.Create()
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{"session_id": sessionID})
}



func (h *Handler) handleLoadQuestions(w http.ResponseWriter, r *http.Request) {
    var questions []model.Question
    if err := json.NewDecoder(r.Body).Decode(&questions); err != nil {
        http.Error(w, "Invalid JSON", http.StatusBadRequest)
        return
    }
    if len(questions) == 0 {
        http.Error(w, "No questions provided", http.StatusBadRequest)
        return
    }
    h.Engine.LoadQuestions(questions)
    logger.Info.Printf("Loaded %d questions via API", len(questions))
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]interface{}{
        "status": "ok",
        "count":  len(questions),
    })
}
func (h *Handler) auth(next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        if h.Config.Server.Token != "" {
            if r.Header.Get("X-Token") != h.Config.Server.Token {
                http.Error(w, "Unauthorized", http.StatusUnauthorized)
                return
            }
        }
        next(w, r)
    }
}
