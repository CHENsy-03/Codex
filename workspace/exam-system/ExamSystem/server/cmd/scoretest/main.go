package main

import (
    "fmt"
    "examsystem/internal/engine"
    "examsystem/model"
)

func main() {
    questions := make([]model.Question, 100)
    for i := range questions {
        id := i + 1
        questions[i] = model.Question{
            ID:      id,
            Text:    fmt.Sprintf("Question %d", id),
            Options: map[string]string{"A": "A Opt", "B": "B Opt", "C": "C Opt", "D": "D Opt"},
            Answer:  "A",
            Score:   1,
        }
    }

    eng := engine.New()
    eng.LoadQuestions(questions)
	sess := eng.CreateSession()

    for i := 1; i <= 95; i++ {
        sess.Answer(i, "A")
    }
    for i := 96; i <= 100; i++ {
        sess.Answer(i, "B")
    }

    result := sess.Submit()
    fmt.Printf("考试结果:%d", result.EarnedScore)
}
