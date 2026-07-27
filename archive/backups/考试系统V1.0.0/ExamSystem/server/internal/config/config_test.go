package config

import (
    "os"
    "testing"
)

func TestConfigMinimal(t *testing.T) {
    content := []byte("server:\n  port: 9090\n")
    tmp, err := os.CreateTemp("", "config*.yaml")
    if err != nil {
        t.Fatal(err)
    }
    defer os.Remove(tmp.Name())
    tmp.Write(content)
    tmp.Close()

    cfg, err := Load(tmp.Name())
    if err != nil {
        t.Fatalf("Load failed: %v", err)
    }
    if cfg.Server.Port != 9090 {
        t.Errorf("Port = %d, want 9090", cfg.Server.Port)
    }
}

func TestConfigDefaultPort(t *testing.T) {
    content := []byte("data:\n  path: \"test\"\nlog:\n  server: \"test.log\"\n")
    tmp, _ := os.CreateTemp("", "config*.yaml")
    defer os.Remove(tmp.Name())
    tmp.Write(content)
    tmp.Close()

    cfg, err := Load(tmp.Name())
    if err != nil {
        t.Fatalf("Load failed: %v", err)
    }
    if cfg.Server.Port != 8080 {
        t.Errorf("default Port = %d, want 8080", cfg.Server.Port)
    }
}

func TestConfigFull(t *testing.T) {
    content := []byte("server:\n  port: 8080\n  token: \"test-token\"\ndata:\n  path: \"data/questions\"\n  session_dir: \"data/sessions\"\nlog:\n  server: \"logs/server.log\"\n  error: \"logs/error.log\"\nexam:\n  show_answer_after_submit: false\n")
    tmp, _ := os.CreateTemp("", "config*.yaml")
    defer os.Remove(tmp.Name())
    tmp.Write(content)
    tmp.Close()

    cfg, err := Load(tmp.Name())
    if err != nil {
        t.Fatalf("Load failed: %v", err)
    }
    if cfg.Data.Path != "data/questions" {
        t.Errorf("Data.Path = %q, want %q", cfg.Data.Path, "data/questions")
    }
    if cfg.Exam.ShowAnswerAfterSubmit != false {
        t.Error("ShowAnswerAfterSubmit should be false")
    }
}
