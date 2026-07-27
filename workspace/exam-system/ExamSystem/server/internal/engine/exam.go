package engine

import "examsystem/model"

type AnswerRecord struct {
    Question    *model.Question
    Chosen      string
    IsCorrect   bool
    EarnedScore int
}

type ExamResult struct {
    TotalScore   int
    EarnedScore  int
    CorrectCount int
    TotalCount   int
    Records      []AnswerRecord
}
