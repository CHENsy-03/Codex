package engine

import "examsystem/model"

type Engine struct {
    Questions []model.Question
    QuestionMap map[int]*model.Question
}

func New() *Engine {
    return &Engine{
        QuestionMap: make(map[int]*model.Question),
    }
}

func (e *Engine) LoadQuestions(qs []model.Question) {
    e.Questions = qs
    e.QuestionMap = make(map[int]*model.Question, len(qs))
    for i := range qs {
        e.QuestionMap[qs[i].ID] = &qs[i]
    }
}

func (e *Engine) GetQuestionCount() int {
    return len(e.Questions)
}
