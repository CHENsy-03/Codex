package main

import (
    "flag"
    "log"

    "examsystem/internal/api"
    "examsystem/internal/config"
    "examsystem/internal/logger"
    "examsystem/internal/storage"
)

func main() {
    configPath := flag.String("config", "config.yaml", "Path to config.yaml")
    questionsPath := flag.String("questions", "", "Path to questions.json (overrides config)")
    flag.Parse()

    cfg, err := config.Load(*configPath)
    if err != nil {
        cfg, err = config.Load("../config/config.yaml")
    }
    if err != nil {
        cfg, err = config.Load("./config/config.yaml")
    }
    if err != nil {
        cfg, err = config.Load("../config.yaml")
    }
    if err != nil {
        log.Fatalf("Failed to load config, tried: %s, ../config/config.yaml, ./config/config.yaml, ../config.yaml", *configPath)
    }
    logger.InitFromConfig(cfg.Log.Server, cfg.Log.Error)
    // fallback to legacy Path field
    if cfg.Log.Server == "" && cfg.Log.Error == "" && cfg.Log.Path != "" {
        logger.InitFromPath(cfg.Log.Path)
    }
    srv := api.NewServer(cfg)

    loadPath := *questionsPath
    if loadPath == "" {
        loadPath = cfg.Data.Path
    }
    qs, err := storage.LoadQuestionsFromFile(loadPath)
    if err != nil {
        log.Fatalf("加载题库失败: %v", err)
    }
    if len(qs) == 0 {
        log.Fatalf("题库为空: %s", loadPath)
    }
    logger.Info.Printf("加载 %d 题成功", len(qs))
    srv.Engine.LoadQuestions(qs)

    if err := srv.Start(); err != nil {
        log.Fatalf("Server failed: %v", err)
    }
}
