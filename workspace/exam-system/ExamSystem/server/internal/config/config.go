package config

import (
    "os"
    "gopkg.in/yaml.v3"
)

type ExamConfig struct {
    ShowAnswerAfterSubmit bool `yaml:"show_answer_after_submit"`
}

type Config struct {
    Server ServerConfig `yaml:"server"`
    Data   DataConfig   `yaml:"data"`
    Log    LogConfig    `yaml:"log"`
    Exam   ExamConfig   `yaml:"exam"`
}

type ServerConfig struct {
    Port  int    `yaml:"port"`
    Token string `yaml:"token"`
}

type DataConfig struct {
    Path       string `yaml:"path"`
    SessionDir string `yaml:"session_dir"`
}

type LogConfig struct {
    Path   string `yaml:"path"`   // legacy fallback
    Server string `yaml:"server"`
    Error  string `yaml:"error"`
}

func Load(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, err
    }
    var cfg Config
    if err := yaml.Unmarshal(data, &cfg); err != nil {
        return nil, err
    }
    if cfg.Server.Port == 0 {
        cfg.Server.Port = 8080
    }
    return &cfg, nil
}
