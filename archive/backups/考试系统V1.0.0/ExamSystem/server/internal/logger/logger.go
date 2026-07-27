package logger

import (
    "io"
    "log"
    "os"
    "path/filepath"
)

var (
    Info  *log.Logger
    Warn  *log.Logger
    Error *log.Logger
)

func Init() {
    flags := log.Ldate | log.Ltime | log.Lmsgprefix
    Info = log.New(os.Stdout, "[INFO] ", flags)
    Warn = log.New(os.Stdout, "[WARN] ", flags)
    Error = log.New(os.Stderr, "[ERROR] ", flags)
}

func SetOutput(w io.Writer) {
    flags := log.Ldate | log.Ltime | log.Lmsgprefix
    Info = log.New(w, "[INFO] ", flags)
    Warn = log.New(w, "[WARN] ", flags)
    Error = log.New(w, "[ERROR] ", flags)
}

func InitFromConfig(serverPath, errorPath string) {
    flags := log.Ldate | log.Ltime | log.Lmsgprefix
    // Server log: Info + Warn
    if serverPath != "" {
        dir := filepath.Dir(serverPath)
        os.MkdirAll(dir, 0755)
        f, err := os.OpenFile(serverPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
        if err == nil {
            Info = log.New(f, "[INFO] ", flags)
            Warn = log.New(f, "[WARN] ", flags)
        } else {
            Info = log.New(os.Stdout, "[INFO] ", flags)
            Warn = log.New(os.Stdout, "[WARN] ", flags)
        }
    } else {
        Info = log.New(os.Stdout, "[INFO] ", flags)
        Warn = log.New(os.Stdout, "[WARN] ", flags)
    }
    // Error log
    if errorPath != "" {
        dir := filepath.Dir(errorPath)
        os.MkdirAll(dir, 0755)
        f, err := os.OpenFile(errorPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
        if err == nil {
            Error = log.New(f, "[ERROR] ", flags)
        } else {
            Error = log.New(os.Stderr, "[ERROR] ", flags)
        }
    } else {
        Error = log.New(os.Stderr, "[ERROR] ", flags)
    }
}

func InitFromPath(path string) {
    if path == "" {
        Init()
        return
    }
    dir := filepath.Dir(path)
    os.MkdirAll(dir, 0755)
    f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
    if err != nil {
        Init()
        return
    }
    SetOutput(f)
}
