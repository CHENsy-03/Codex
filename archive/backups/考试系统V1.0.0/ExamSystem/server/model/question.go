package model

type Question struct {
    ID      int               `json:"id"`
    Text    string            `json:"text"`
    Options map[string]string `json:"options"`
    Answer  string            `json:"answer"`
    Score   int               `json:"score"`
    Type    string            `json:"type,omitempty"`
}
