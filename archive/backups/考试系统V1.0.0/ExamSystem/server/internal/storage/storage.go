package storage

import (
    "encoding/json"
    "os"
    "examsystem/model"
)

type Storage struct {
    DataDir string
}

func New(dataDir string) *Storage {
    return &Storage{DataDir: dataDir}
}

func (s *Storage) SaveQuestions(qs []model.Question, path string) error {
    data, err := json.MarshalIndent(qs, "", "  ")
    if err != nil {
        return err
    }
    const perm = 0o644
    return os.WriteFile(path, data, perm)
}
