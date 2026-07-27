package engine

import (
    "fmt"
)

// ExamSession holds per-submission state (answers + cached result).
// Multiple sessions can exist simultaneously for different clients.
type ExamSession struct {
    engine  *Engine
    Answers map[int]string
    result  *ExamResult
}

func (e *Engine) CreateSession() *ExamSession {
    return &ExamSession{
        engine:  e,
        Answers: make(map[int]string),
    }
}

func (s *ExamSession) GetQuestionCount() int {
    return len(s.engine.Questions)
}

func (s *ExamSession) Answer(qid int, choice string) error {
    q := s.engine.QuestionMap[qid]
    if q == nil {
        return fmt.Errorf("question #%d not found", qid)
    }
    if _, ok := q.Options[choice]; !ok {
        return fmt.Errorf("invalid choice %q for question #%d", choice, qid)
    }
    s.Answers[qid] = choice
    return nil
}

func (s *ExamSession) GetUnansweredCount() int {
    count := 0
    for _, q := range s.engine.Questions {
        if _, ok := s.Answers[q.ID]; !ok {
            count++
        }
    }
    return count
}

func (s *ExamSession) GetTotalScore() int {
    total := 0
    for _, q := range s.engine.Questions {
        total += q.Score
    }
    return total
}

func (s *ExamSession) Submit() ExamResult {
    if s.result != nil {
        return *s.result
    }
    var records []AnswerRecord
    earned := 0
    correctCount := 0
    for i := range s.engine.Questions {
        q := &s.engine.Questions[i]
        chosen := s.Answers[q.ID]
        correct := false
        correct = compareAnswer(chosen, q.Answer)
        scoreEarned := 0
        if correct {
            correctCount++
            scoreEarned = q.Score
        }
        earned += scoreEarned
        records = append(records, AnswerRecord{
            Question:    q,
            Chosen:      chosen,
            IsCorrect:   correct,
            EarnedScore: scoreEarned,
        })
    }
    result := ExamResult{
        TotalScore:   s.GetTotalScore(),
        EarnedScore:  earned,
        CorrectCount: correctCount,
        TotalCount:   len(s.engine.Questions),
        Records:      records,
    }
    s.result = &result
    return result
}

func (s *ExamSession) CalculateScore() int {
    total := 0
    for i := range s.engine.Questions {
        q := &s.engine.Questions[i]
        chosen := s.Answers[q.ID]
        if compareAnswer(chosen, q.Answer) {
            total += q.Score
        }
    }
    return total
}

func compareAnswer(chosen, correct string) bool {
    if chosen == "" {
        return false
    }
    chosen = unique(chosen)
    correct = unique(correct)
    if len(chosen) != len(correct) {
        return false
    }
    if len(chosen) <= 1 {
        return chosen == correct
    }
    cm := make(map[rune]bool)
    for _, c := range chosen {
        cm[c] = true
    }
    for _, c := range correct {
        if !cm[c] {
            return false
        }
    }
    return true
}

func unique(s string) string {
    seen := make(map[rune]bool)
    result := make([]rune, 0, len(s))
    for _, c := range s {
        if !seen[c] {
            seen[c] = true
            result = append(result, c)
        }
    }
    return string(result)
}
