package engine

import (
    "testing"
    "examsystem/model"
)

func TestCreateSession(t *testing.T) {
    eng := New()
    qs := []model.Question{
        {ID: 1, Text: "Q1", Options: map[string]string{"A": "A", "B": "B"}, Answer: "A", Score: 1},
        {ID: 2, Text: "Q2", Options: map[string]string{"A": "A", "B": "B"}, Answer: "B", Score: 2},
    }
    eng.LoadQuestions(qs)
    sess := eng.CreateSession()
    if n := sess.GetQuestionCount(); n != 2 {
        t.Errorf("GetQuestionCount = %d, want 2", n)
    }
    if n := sess.GetTotalScore(); n != 3 {
        t.Errorf("GetTotalScore = %d, want 3", n)
    }
    if n := sess.GetUnansweredCount(); n != 2 {
        t.Errorf("GetUnansweredCount = %d, want 2", n)
    }
}

func TestAnswer(t *testing.T) {
    eng := New()
    eng.LoadQuestions([]model.Question{
        {ID: 1, Text: "Q", Options: map[string]string{"A": "A", "B": "B"}, Answer: "A", Score: 1},
    })
    sess := eng.CreateSession()

    if err := sess.Answer(1, "A"); err != nil {
        t.Errorf("valid answer: %v", err)
    }
    if err := sess.Answer(1, "X"); err == nil {
        t.Error("invalid choice should error")
    }
    if err := sess.Answer(999, "A"); err == nil {
        t.Error("unknown qid should error")
    }
}

func TestSubmit(t *testing.T) {
    eng := New()
    eng.LoadQuestions([]model.Question{
        {ID: 1, Text: "Q1", Options: map[string]string{"A": "A", "B": "B"}, Answer: "A", Score: 1},
        {ID: 2, Text: "Q2", Options: map[string]string{"A": "A", "B": "B"}, Answer: "B", Score: 2},
    })
    sess := eng.CreateSession()
    sess.Answer(1, "A") // correct
    sess.Answer(2, "A") // wrong

    r := sess.Submit()
    if r.TotalScore != 3 {
        t.Errorf("TotalScore = %d, want 3", r.TotalScore)
    }
    if r.EarnedScore != 1 {
        t.Errorf("EarnedScore = %d, want 1", r.EarnedScore)
    }
    if r.CorrectCount != 1 {
        t.Errorf("CorrectCount = %d, want 1", r.CorrectCount)
    }
    if r.TotalCount != 2 {
        t.Errorf("TotalCount = %d, want 2", r.TotalCount)
    }
}

func TestSubmitIdempotent(t *testing.T) {
    eng := New()
    eng.LoadQuestions([]model.Question{
        {ID: 1, Text: "Q", Options: map[string]string{"A": "A"}, Answer: "A", Score: 1},
    })
    sess := eng.CreateSession()
    sess.Answer(1, "A")
    r1 := sess.Submit()
    r2 := sess.Submit()
    if r1.EarnedScore != r2.EarnedScore {
        t.Error("Submit should be idempotent")
    }
    if r1.TotalScore != r2.TotalScore {
        t.Error("Submit should return same result")
    }
}

func TestAllWrong(t *testing.T) {
    eng := New()
    eng.LoadQuestions([]model.Question{
        {ID: 1, Text: "Q1", Options: map[string]string{"A": "A"}, Answer: "A", Score: 5},
        {ID: 2, Text: "Q2", Options: map[string]string{"B": "B"}, Answer: "B", Score: 3},
    })
    sess := eng.CreateSession()
    // no answers given
    r := sess.Submit()
    if r.EarnedScore != 0 {
        t.Errorf("EarnedScore = %d, want 0", r.EarnedScore)
    }
    if r.CorrectCount != 0 {
        t.Errorf("CorrectCount = %d, want 0", r.CorrectCount)
    }
}

func TestCalculateScore(t *testing.T) {
    eng := New()
    eng.LoadQuestions([]model.Question{
        {ID: 1, Text: "Q", Options: map[string]string{"A": "A", "B": "B"}, Answer: "A", Score: 10},
    })
    sess := eng.CreateSession()
    sess.Answer(1, "A")
    if s := sess.CalculateScore(); s != 10 {
        t.Errorf("CalculateScore = %d, want 10", s)
    }
}
