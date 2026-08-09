package com.drone.worker;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class WorkerCommandLineTest {

    @Test
    void pythonFactoryUsesAbsoluteCommandListAndCwd() {
        Path python = Path.of("C:/Python 3.14/python.exe");
        Path project = Path.of("D:/地图 项目/无人机样品");
        WorkerCommandLine cl = WorkerCommandLine.forPythonWorker(python, project);

        List<String> command = cl.command();
        assertEquals(3, command.size());
        assertEquals(python.toString(), command.get(0));
        assertEquals("-u", command.get(1));
        assertEquals(project.resolve("worker_main.py").toString(), command.get(2));
        assertEquals(project.toAbsolutePath().normalize(), cl.workingDirectory());

        // 空格与中文保持完整（独立参数，非 shell 字符串）
        assertTrue(command.get(0).contains("Python 3.14"));
        assertTrue(command.get(2).contains("地图 项目"));
        assertEquals("1", cl.environment().get("PYTHONUTF8"));
        assertEquals("utf-8", cl.environment().get("PYTHONIOENCODING"));
    }

    @Test
    void relativePathsRejected() {
        assertThrows(IllegalArgumentException.class,
                () -> WorkerCommandLine.forPythonWorker(Path.of("python.exe"), Path.of("C:/proj")));
        assertThrows(IllegalArgumentException.class,
                () -> WorkerCommandLine.forPythonWorker(Path.of("C:/python.exe"), Path.of("proj")));
    }

    @Test
    void emptyCommandRejected() {
        assertThrows(IllegalArgumentException.class,
                () -> new WorkerCommandLine(List.of(), Path.of("C:/p"), Map.of()));
        assertThrows(IllegalArgumentException.class,
                () -> new WorkerCommandLine(List.of("a", ""), Path.of("C:/p"), Map.of()));
    }

    @Test
    void commandAndEnvironmentAreDefensivelyCopied() {
        List<String> mutable = new ArrayList<>(List.of("a", "b"));
        Map<String, String> mutableEnv = new java.util.LinkedHashMap<>();
        mutableEnv.put("K", "V");
        WorkerCommandLine cl = new WorkerCommandLine(mutable, Path.of("C:/p"), mutableEnv);

        mutable.add("c");
        mutableEnv.put("K2", "V2");

        assertEquals(2, cl.command().size());
        assertThrows(UnsupportedOperationException.class, () -> cl.command().add("x"));
        assertThrows(UnsupportedOperationException.class, () -> cl.environment().put("x", "y"));
        assertEquals("V", cl.environment().get("K"));
    }
}
