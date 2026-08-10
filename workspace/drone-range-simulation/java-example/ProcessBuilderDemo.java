/*
 * ProcessBuilderDemo — 外部系统调用 Nuitka standalone Worker 的单文件示例。
 *
 * 纯 JDK 21，默认包，无任何第三方依赖（不使用 Jackson）。
 * 通过本地 ProcessBuilder 启动软件目录中的 drone-range-worker.exe，
 * 依次演示：hello -> load_map -> calculate（距离 + 飞行时间）-> shutdown。
 *
 * 用法: java ProcessBuilderDemo <drone-range-worker.exe> <GeoTIFF路径>
 * 说明: 所有路径来自命令行参数；坐标为虚构示例；stdout 仅协议 JSON，
 *       stderr 独立排空（仅日志）。
 */

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

public class ProcessBuilderDemo {

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("用法: java ProcessBuilderDemo <drone-range-worker.exe> <GeoTIFF路径>");
            System.exit(2);
        }
        Path executable = Path.of(args[0]).toAbsolutePath();
        Path geotiff = Path.of(args[1]).toAbsolutePath();

        if (!Files.isRegularFile(executable)) {
            System.err.println("找不到可执行文件: " + executable);
            System.exit(2);
        }
        if (!Files.isRegularFile(geotiff)) {
            System.err.println("找不到 GeoTIFF: " + geotiff);
            System.exit(2);
        }

        try (WorkerProcess worker = new WorkerProcess(executable)) {
            long seq = 0;

            Map<String, Object> hello = worker.request("h-" + (++seq),
                    "\"operation\":\"hello\"");
            requireSuccess(hello, "hello");
            System.out.println("hello: protocolVersion=" + field(hello, "data.protocolVersion")
                    + " engineVersion=" + field(hello, "data.engineVersion")
                    + " state=" + field(hello, "data.state"));

            Map<String, Object> loaded = worker.request("m-" + (++seq),
                    "\"operation\":\"load_map\",\"path\":" + Json.escape(geotiff.toString()));
            requireSuccess(loaded, "load_map");
            System.out.println("load_map: crs=" + field(loaded, "data.crs")
                    + " " + field(loaded, "data.width") + "x" + field(loaded, "data.height")
                    + " bands=" + field(loaded, "data.bands"));

            Map<String, Object> calc = worker.request("c-" + (++seq),
                    "\"operation\":\"calculate\","
                            + "\"pointA\":{\"type\":\"wgs84\",\"longitude\":104.123456,\"latitude\":30.654321},"
                            + "\"pointB\":{\"type\":\"pixel\",\"column\":10.5,\"row\":20.5},"
                            + "\"speedMps\":10");
            requireSuccess(calc, "calculate");
            System.out.println("calculate: distance=" + field(calc, "data.distanceMeters")
                    + " exact=" + field(calc, "data.exactSeconds")
                    + " rounded=" + field(calc, "data.roundedSeconds")
                    + " duration=" + field(calc, "data.duration"));

            Map<String, Object> shutdown = worker.request("s-" + (++seq),
                    "\"operation\":\"shutdown\"");
            requireSuccess(shutdown, "shutdown");
            System.out.println("shutdown: state=" + field(shutdown, "data.state"));

            int exitCode = worker.awaitExit(10, TimeUnit.SECONDS);
            System.out.println("worker exit code=" + exitCode);
        }
    }

    private static void requireSuccess(Map<String, Object> response, String operation) {
        if (!Boolean.TRUE.equals(response.get("success"))) {
            System.err.println(operation + " 失败: "
                    + response.get("error"));
            System.exit(1);
        }
    }

    /** 从解析后的响应中读取点分路径字段（如 data.crs）。 */
    private static String field(Map<String, Object> root, String dotted) {
        Object current = root;
        for (String part : dotted.split("\\.")) {
            if (!(current instanceof Map<?, ?> map)) {
                return null;
            }
            current = map.get(part);
        }
        return String.valueOf(current);
    }

    /** 常驻 Worker 进程封装：UTF-8 单行 NDJSON、串行请求、按 id 关联响应。 */
    static final class WorkerProcess implements AutoCloseable {
        private final Process process;
        private final BufferedWriter stdin;
        private final BufferedReader stdout;
        private final Thread stderrDrain;

        WorkerProcess(Path executable) throws IOException {
            ProcessBuilder pb = new ProcessBuilder(executable.toString());
            pb.directory(executable.getParent().toFile());
            pb.redirectErrorStream(false);
            process = pb.start();
            stdin = new BufferedWriter(
                    new OutputStreamWriter(process.getOutputStream(), StandardCharsets.UTF_8));
            stdout = new BufferedReader(
                    new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8));
            BufferedReader stderr = new BufferedReader(
                    new InputStreamReader(process.getErrorStream(), StandardCharsets.UTF_8));
            stderrDrain = new Thread(() -> {
                try {
                    while (stderr.readLine() != null) {
                        // stderr 仅为日志通道，独立排空，不进入业务响应。
                    }
                } catch (IOException ignored) {
                    // 通道结束即忽略。
                }
            });
            stderrDrain.setDaemon(true);
            stderrDrain.start();
        }

        Map<String, Object> request(String id, String body) throws IOException {
            String line = "{\"id\":" + Json.escape(id) + ",\"protocolVersion\":1," + body + "}";
            stdin.write(line);
            stdin.write('\n');
            stdin.flush();

            while (true) {
                String responseLine = stdout.readLine();
                if (responseLine == null) {
                    throw new IOException("Worker 提前退出，exit=" + process.exitValue());
                }
                Map<String, Object> response = Json.parseObject(responseLine);
                if (id.equals(String.valueOf(response.get("id")))) {
                    return response;
                }
            }
        }

        int awaitExit(long timeout, TimeUnit unit) throws InterruptedException {
            if (!process.waitFor(timeout, unit)) {
                process.destroy();
                if (!process.waitFor(2, TimeUnit.SECONDS)) {
                    process.destroyForcibly();
                }
            }
            return process.exitValue();
        }

        @Override
        public void close() {
            try {
                stdin.close();
            } catch (IOException ignored) {
                // 已关闭。
            }
            if (process.isAlive()) {
                process.destroy();
                try {
                    if (!process.waitFor(2, TimeUnit.SECONDS)) {
                        process.destroyForcibly();
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    process.destroyForcibly();
                }
            }
        }
    }
}

/** 极简 JSON 工具：字符串转义与递归下降解析（仅支持协议所需子集）。 */
final class Json {
    private Json() {
    }

    static String escape(String value) {
        StringBuilder out = new StringBuilder();
        out.append('"');
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\n' -> out.append("\\n");
                case '\r' -> out.append("\\r");
                case '\t' -> out.append("\\t");
                case '\b' -> out.append("\\b");
                case '\f' -> out.append("\\f");
                default -> {
                    if (c < 0x20) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
                }
            }
        }
        return out.append('"').toString();
    }

    @SuppressWarnings("unchecked")
    static Map<String, Object> parseObject(String text) {
        Parser parser = new Parser(text);
        Object value = parser.parseValue();
        if (!(value instanceof Map)) {
            throw new IllegalArgumentException("JSON 根节点不是对象: " + text);
        }
        return (Map<String, Object>) value;
    }

    private static final class Parser {
        private final String text;
        private int pos;

        Parser(String text) {
            this.text = text;
        }

        Object parseValue() {
            skipWhitespace();
            if (pos >= text.length()) {
                throw new IllegalArgumentException("JSON 提前结束");
            }
            return switch (text.charAt(pos)) {
                case '{' -> parseObject();
                case '[' -> parseArray();
                case '"' -> parseString();
                case 't' -> parseLiteral("true", Boolean.TRUE);
                case 'f' -> parseLiteral("false", Boolean.FALSE);
                case 'n' -> parseLiteral("null", null);
                default -> parseNumber();
            };
        }

        private Map<String, Object> parseObject() {
            Map<String, Object> result = new LinkedHashMap<>();
            pos++; // '{'
            skipWhitespace();
            if (peek() == '}') {
                pos++;
                return result;
            }
            while (true) {
                skipWhitespace();
                String key = parseString();
                skipWhitespace();
                expect(':');
                result.put(key, parseValue());
                skipWhitespace();
                char c = next();
                if (c == '}') {
                    return result;
                }
                if (c != ',') {
                    throw new IllegalArgumentException("对象缺少逗号: " + text);
                }
            }
        }

        private List<Object> parseArray() {
            List<Object> result = new ArrayList<>();
            pos++; // '['
            skipWhitespace();
            if (peek() == ']') {
                pos++;
                return result;
            }
            while (true) {
                result.add(parseValue());
                skipWhitespace();
                char c = next();
                if (c == ']') {
                    return result;
                }
                if (c != ',') {
                    throw new IllegalArgumentException("数组缺少逗号: " + text);
                }
            }
        }

        private String parseString() {
            if (next() != '"') {
                throw new IllegalArgumentException("期望字符串: " + text);
            }
            StringBuilder out = new StringBuilder();
            while (true) {
                if (pos >= text.length()) {
                    throw new IllegalArgumentException("字符串未闭合");
                }
                char c = text.charAt(pos++);
                if (c == '"') {
                    return out.toString();
                }
                if (c != '\\') {
                    out.append(c);
                    continue;
                }
                if (pos >= text.length()) {
                    throw new IllegalArgumentException("转义未闭合");
                }
                char e = text.charAt(pos++);
                switch (e) {
                    case '"' -> out.append('"');
                    case '\\' -> out.append('\\');
                    case '/' -> out.append('/');
                    case 'b' -> out.append('\b');
                    case 'f' -> out.append('\f');
                    case 'n' -> out.append('\n');
                    case 'r' -> out.append('\r');
                    case 't' -> out.append('\t');
                    case 'u' -> {
                        if (pos + 4 > text.length()) {
                            throw new IllegalArgumentException("\\u 转义过短");
                        }
                        out.append((char) Integer.parseInt(text.substring(pos, pos + 4), 16));
                        pos += 4;
                    }
                    default -> throw new IllegalArgumentException("未知转义 \\" + e);
                }
            }
        }

        private Object parseNumber() {
            int start = pos;
            if (peek() == '-') {
                pos++;
            }
            while (pos < text.length() && "0123456789.eE+-".indexOf(text.charAt(pos)) >= 0) {
                pos++;
            }
            String raw = text.substring(start, pos);
            try {
                if (raw.indexOf('.') < 0 && raw.indexOf('e') < 0 && raw.indexOf('E') < 0) {
                    return Long.parseLong(raw);
                }
                return Double.parseDouble(raw);
            } catch (NumberFormatException e) {
                throw new IllegalArgumentException("非法数字: " + raw);
            }
        }

        private Object parseLiteral(String literal, Object value) {
            if (!text.startsWith(literal, pos)) {
                throw new IllegalArgumentException("非法字面量: " + text.substring(pos));
            }
            pos += literal.length();
            return value;
        }

        private void skipWhitespace() {
            while (pos < text.length() && Character.isWhitespace(text.charAt(pos))) {
                pos++;
            }
        }

        private char peek() {
            return pos < text.length() ? text.charAt(pos) : '\0';
        }

        private char next() {
            if (pos >= text.length()) {
                throw new IllegalArgumentException("JSON 提前结束");
            }
            return text.charAt(pos++);
        }

        private void expect(char expected) {
            if (next() != expected) {
                throw new IllegalArgumentException("期望字符 " + expected + ": " + text);
            }
        }
    }
}