package com.uav.sdk;
public class Example {
    public static void main(String[] args) throws Exception {
        UavClient client = new UavClient("http://127.0.0.1:8080");
        // Login
        String loginResp = client.login("admin", "admin123");
        System.out.println("Login: " + loginResp);
        // Create project
        String projectResp = client.createProject("Mountain Survey", "Shaoxing", "Zhang San");
        System.out.println("Project: " + projectResp);
        // Register device
        String deviceResp = client.registerDevice("RTK001", "GNSS", "K803");
        System.out.println("Device: " + deviceResp);
        // Device status
        String statusResp = client.deviceStatus("RTK001");
        System.out.println("Status: " + statusResp);
        // Upload survey data
        String surveyResp = client.surveyUpload("P001", "RTK001,30.5,120.2,50.0\nRTK001,30.51,120.21,50.5");
        System.out.println("Survey: " + surveyResp);
    }
}
