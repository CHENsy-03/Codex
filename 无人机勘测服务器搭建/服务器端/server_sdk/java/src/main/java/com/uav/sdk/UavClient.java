package com.uav.sdk;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
/** V2.1 Java SDK Client - mirrors Python UavClient */
public class UavClient {
    private String baseUrl;
    private String token;
    public UavClient(String baseUrl) { this.baseUrl = baseUrl.replaceAll("/$", ""); }
    public void setToken(String token) { this.token = token; }
    public String getToken() { return token; }
    private String req(String method, String path, String body) throws IOException {
        URL url = new URL(baseUrl + path);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod(method);
        conn.setRequestProperty("Content-Type", "application/json");
        if (token != null) conn.setRequestProperty("Authorization", "Bearer " + token);
        conn.setDoOutput(body != null);
        if (body != null) {
            try (OutputStream os = conn.getOutputStream()) { os.write(body.getBytes(StandardCharsets.UTF_8)); }
        }
        int status = conn.getResponseCode();
        InputStream is = (status >= 200 && status < 300) ? conn.getInputStream() : conn.getErrorStream();
        StringBuilder sb = new StringBuilder();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8))) {
            String line; while ((line = br.readLine()) != null) sb.append(line);
        }
        return sb.toString();
    }
    public String login(String username, String password) throws IOException {
        String r = req("POST", "/api/v1/auth/login",
            "{\"username\":\"" + username + "\",\"password\":\"" + password + "\"}");
        token = extractJsonString(r, "token");
        return r;
    }
    public String createProject(String name, String location, String operator) throws IOException {
        return req("POST", "/api/v1/project/create",
            "{\"project_name\":\"" + name + "\",\"location\":\"" + location + "\",\"operator\":\"" + operator + "\"}");
    }
    public String getProject(String pid) throws IOException { return req("GET", "/api/v1/project/" + pid, null); }
    public String listProjects() throws IOException { return req("GET", "/api/v1/project/list", null); }
    public String registerDevice(String deviceId, String type, String model) throws IOException {
        return req("POST", "/api/v1/device/register",
            "{\"device_id\":\"" + deviceId + "\",\"type\":\"" + type + "\",\"model\":\"" + model + "\"}");
    }
    public String deviceStatus(String deviceId) throws IOException {
        return req("GET", "/api/v1/device/status/" + deviceId, null);
    }
    public String deviceList() throws IOException { return req("GET", "/api/v1/device/list", null); }
    public String startTask(String deviceId, String projectId, int duration) throws IOException {
        return req("POST", "/api/v1/task/start",
            "{\"device_id\":\"" + deviceId + "\",\"project_id\":\"" + projectId + "\",\"duration\":" + duration + "}");
    }
    public String taskStatus(String taskId) throws IOException {
        return req("GET", "/api/v1/task/status/" + taskId, null);
    }
    public String positionLatest(String deviceId) throws IOException {
        return req("GET", "/api/v1/position/latest/" + deviceId, null);
    }
    public String resultGet(String projectId) throws IOException {
        return req("GET", "/api/v1/result/" + projectId, null);
    }
    public String surveyUpload(String projectId, String csvData) throws IOException {
        return req("POST", "/api/v1/survey/upload",
            "{\"project_id\":\"" + projectId + "\",\"data\":\"" + escapeJson(csvData) + "\"}");
    }
    private static String extractJsonString(String json, String key) {
        String search = "\"" + key + "\":\"";
        int start = json.indexOf(search);
        if (start < 0) return null;
        start += search.length();
        int end = json.indexOf("\"", start);
        return end > start ? json.substring(start, end) : null;
    }
    private static String escapeJson(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r");
    }
}
