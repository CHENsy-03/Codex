package com.drone.worker;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * 不可变的 Worker 启动命令：参数列表、工作目录与必要环境变量。
 * 不使用 shell 字符串拼接；路径含空格或中文时仍按独立参数传递。
 */
public final class WorkerCommandLine {

    private final List<String> command;
    private final Path workingDirectory;
    private final Map<String, String> environment;

    public WorkerCommandLine(List<String> command, Path workingDirectory, Map<String, String> environment) {
        Objects.requireNonNull(command, "command");
        Objects.requireNonNull(workingDirectory, "workingDirectory");
        Objects.requireNonNull(environment, "environment");
        if (command.isEmpty()) {
            throw new IllegalArgumentException("command 不能为空");
        }
        List<String> copy = new ArrayList<>();
        for (String part : command) {
            if (part == null || part.isEmpty()) {
                throw new IllegalArgumentException("command 参数不能为空");
            }
            copy.add(part);
        }
        this.command = Collections.unmodifiableList(copy);
        this.workingDirectory = workingDirectory.toAbsolutePath().normalize();
        Map<String, String> envCopy = new LinkedHashMap<>();
        environment.forEach((k, v) -> envCopy.put(
                Objects.requireNonNull(k, "环境变量名不能为 null"),
                Objects.requireNonNull(v, "环境变量值不能为 null")));
        this.environment = Collections.unmodifiableMap(envCopy);
    }

    public static WorkerCommandLine forPythonWorker(Path pythonExecutable, Path projectRoot) {
        Objects.requireNonNull(pythonExecutable, "pythonExecutable");
        Objects.requireNonNull(projectRoot, "projectRoot");
        if (!pythonExecutable.isAbsolute()) {
            throw new IllegalArgumentException("python 必须是绝对路径: " + pythonExecutable);
        }
        if (!projectRoot.isAbsolute()) {
            throw new IllegalArgumentException("项目根必须是绝对路径: " + projectRoot);
        }
        Path workerMain = projectRoot.resolve("worker_main.py");
        List<String> command = List.of(pythonExecutable.toString(), "-u", workerMain.toString());
        Map<String, String> env = new LinkedHashMap<>();
        env.put("PYTHONUTF8", "1");
        env.put("PYTHONIOENCODING", "utf-8");
        return new WorkerCommandLine(command, projectRoot, env);
    }
    public static WorkerCommandLine forStandaloneWorker(Path executable, Path workingDirectory) {
        Objects.requireNonNull(executable, "executable");
        Objects.requireNonNull(workingDirectory, "workingDirectory");
        if (!executable.isAbsolute()) {
            throw new IllegalArgumentException("可执行文件必须是绝对路径: " + executable);
        }
        if (!workingDirectory.isAbsolute()) {
            throw new IllegalArgumentException("工作目录必须是绝对路径: " + workingDirectory);
        }
        // standalone 软件目录可执行文件：无附加参数、不设置 Python 解释器专用环境变量
        // （WorkerProcessHandle 使用 environment().putAll 叠加，空图继承父环境 PATH）。
        List<String> command = List.of(executable.toString());
        return new WorkerCommandLine(command, workingDirectory, Map.of());
    }

    public List<String> command() {
        return command;
    }

    public Path workingDirectory() {
        return workingDirectory;
    }

    public Map<String, String> environment() {
        return environment;
    }
}
