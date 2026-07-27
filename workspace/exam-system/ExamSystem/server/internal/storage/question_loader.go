package storage

import (
    "encoding/json"
    "io/fs"
    "os"
    "sort"

    "examsystem/model"
)

type questionFile struct {
    Version    string           `json:"version,omitempty"`
    CreateTime string           `json:"create_time,omitempty"`
    Count      int              `json:"count,omitempty"`
    Questions  []model.Question `json:"questions,omitempty"`
}

func LoadQuestionsFromFile(path string) ([]model.Question, error) {
    // If path is a directory, load all .json files and merge
    if info, err := os.Stat(path); err == nil && info.IsDir() {
        return loadQuestionsFromDir(path)
    }
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, err
    }
    // Try new format: { "version": "2.0", "questions": [...] }
    var qf questionFile
    if err := json.Unmarshal(data, &qf); err == nil && qf.Version != "" {
        return qf.Questions, nil
    }
    // Fall back to old format: plain array [...]
    var questions []model.Question
    if err := json.Unmarshal(data, &questions); err != nil {
        return nil, err
    }
    return questions, nil
}

func loadQuestionsFromDir(dir string) ([]model.Question, error) {
    entries, err := os.ReadDir(dir)
    if err != nil {
        return nil, err
    }
    // Sort to ensure consistent order
    sort.Slice(entries, func(i, j int) bool {
        return entries[i].Name() < entries[j].Name()
    })
    var all []model.Question
    seen := make(map[int]bool)
    for _, e := range entries {
        if e.IsDir() {
            continue
        }
        if len(e.Name()) < 5 || e.Name()[len(e.Name())-5:] != ".json" {
            continue
        }
        qs, err := LoadQuestionsFromFile(dir + "/" + e.Name())
        if err != nil {
            continue
        }
        for i := range qs {
            if !seen[qs[i].ID] {
                seen[qs[i].ID] = true
                all = append(all, qs[i])
            }
        }
    }
    if len(all) == 0 {
        return nil, fs.ErrNotExist
    }
    return all, nil
}
