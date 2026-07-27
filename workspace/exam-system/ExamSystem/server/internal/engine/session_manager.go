package engine

import (
    "crypto/rand"
    "encoding/hex"
    "encoding/json"
    "os"
    "path/filepath"
    "sync"
    "time"

    "examsystem/model"
)

type SessionData struct {
    SessionID   string          `json:"session_id"`
    Status      string          `json:"status"`
    CreatedAt   string          `json:"created_at"`
    SubmittedAt string          `json:"submitted_at,omitempty"`
    QuestionIDs []int           `json:"question_ids,omitempty"`
    Questions   []model.Question   `json:"questions,omitempty"`
    Answers     map[int]string  `json:"answers"`
    Result      *ExamResultData `json:"result,omitempty"`
}

type ExamResultData struct {
    TotalScore   int `json:"total_score"`
    EarnedScore  int `json:"earned_score"`
    CorrectCount int `json:"correct_count"`
    TotalCount   int `json:"total_count"`
}

type SessionManager struct {
    mu          sync.RWMutex
    sessions    map[string]*ExamSession
    engine      *Engine
    sessionsDir string
}

func NewSessionManager(engine *Engine, sessionsDir string) *SessionManager {
    sm := &SessionManager{
        sessions:    make(map[string]*ExamSession),
        engine:      engine,
        sessionsDir: sessionsDir,
    }
    if sessionsDir != "" {
        os.MkdirAll(sessionsDir, 0755)
        sm.loadAllFromDisk()
    }
    return sm
}

func (sm *SessionManager) Create() (*ExamSession, string) {
    sm.mu.Lock()
    defer sm.mu.Unlock()
    b := make([]byte, 16)
    rand.Read(b)
    sessionID := hex.EncodeToString(b)
    sess := sm.engine.CreateSession()
    sm.sessions[sessionID] = sess
    sm.saveLocked(sessionID)
    return sess, sessionID
}

func (sm *SessionManager) Get(sessionID string) *ExamSession {
    sm.mu.RLock()
    sess := sm.sessions[sessionID]
    sm.mu.RUnlock()
    return sess
}

func (sm *SessionManager) SaveAnswer(sessionID string, qid int, choice string) error {
    sm.mu.Lock()
    defer sm.mu.Unlock()
    sess := sm.sessions[sessionID]
    if sess == nil {
        return nil
    }
    if err := sess.Answer(qid, choice); err != nil {
        return err
    }
    sm.saveLocked(sessionID)
    return nil
}

func (sm *SessionManager) SubmitSession(sessionID string) (*ExamResult, error) {
    sm.mu.Lock()
    defer sm.mu.Unlock()
    sess := sm.sessions[sessionID]
    if sess == nil {
        return nil, nil
    }
    result := sess.Submit()
    sm.saveLocked(sessionID)
    return &result, nil
}

func (sm *SessionManager) Delete(sessionID string) {
    sm.mu.Lock()
    defer sm.mu.Unlock()
    delete(sm.sessions, sessionID)
    if sm.sessionsDir != "" {
        os.Remove(filepath.Join(sm.sessionsDir, sessionID+".json"))
    }
}

func (sm *SessionManager) saveLocked(sessionID string) {
    if sm.sessionsDir == "" {
        return
    }
    sess := sm.sessions[sessionID]
    if sess == nil {
        return
    }
    // Preserve original CreatedAt from disk
    createdAt := time.Now().Format(time.RFC3339)
    if existing, err := os.ReadFile(filepath.Join(sm.sessionsDir, sessionID+".json")); err == nil {
        var old SessionData
        if json.Unmarshal(existing, &old) == nil && old.CreatedAt != "" {
            createdAt = old.CreatedAt
        }
    }
    data := SessionData{
        SessionID: sessionID,
        Status:    "active",
        CreatedAt: createdAt,
        Answers:   make(map[int]string),
    }
    data.QuestionIDs = make([]int, len(sm.engine.Questions))
    for i, q := range sm.engine.Questions {
        data.QuestionIDs[i] = q.ID
    }
    data.Questions = make([]model.Question, len(sm.engine.Questions))
    copy(data.Questions, sm.engine.Questions)
    for k, v := range sess.Answers {
        data.Answers[k] = v
    }
    if sess.result != nil {
        data.Status = "submitted"
        data.SubmittedAt = time.Now().Format(time.RFC3339)
        data.Result = &ExamResultData{
            TotalScore:   sess.result.TotalScore,
            EarnedScore:  sess.result.EarnedScore,
            CorrectCount: sess.result.CorrectCount,
            TotalCount:   sess.result.TotalCount,
        }
    }
    raw, _ := json.MarshalIndent(data, "", "  ")
    os.WriteFile(filepath.Join(sm.sessionsDir, sessionID+".json"), raw, 0644)
}

func (sm *SessionManager) loadAllFromDisk() {
    if sm.sessionsDir == "" {
        return
    }
    entries, err := os.ReadDir(sm.sessionsDir)
    if err != nil {
        return
    }
    for _, e := range entries {
        if e.IsDir() || filepath.Ext(e.Name()) != ".json" {
            continue
        }
        sessionID := e.Name()[:len(e.Name())-5]
        raw, err := os.ReadFile(filepath.Join(sm.sessionsDir, e.Name()))
        if err != nil {
            continue
        }
        var data SessionData
        if err := json.Unmarshal(raw, &data); err != nil {
            continue
        }
        sess := sm.engine.CreateSession()
        if len(data.Questions) > 0 {
            tempEng := New()
            tempEng.LoadQuestions(data.Questions)
            sess.engine = tempEng
        }
        for k, v := range data.Answers {
            sess.Answers[k] = v
        }
        if data.Result != nil {
            sess.result = &ExamResult{
                TotalScore:   data.Result.TotalScore,
                EarnedScore:  data.Result.EarnedScore,
                CorrectCount: data.Result.CorrectCount,
                TotalCount:   data.Result.TotalCount,
            }
        }
        sm.sessions[sessionID] = sess
    }
}
