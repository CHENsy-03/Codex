package com.drone.worker;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.Objects;

/**
 * NDJSON 单行编解码。使用 Jackson readTree/writeValueAsString，
 * 禁止启用 default typing；stderr 内容不得送入本类。
 */
public final class NdjsonCodec {

    private final ObjectMapper mapper;

    public NdjsonCodec() {
        this.mapper = new ObjectMapper();
    }

    public NdjsonCodec(ObjectMapper mapper) {
        this.mapper = Objects.requireNonNull(mapper, "mapper");
    }

    public String encodeHello(String id) {
        return writeSingleLine(base(id, "hello"));
    }

    public String encodeLoadMap(String id, String path) {
        ObjectNode root = base(id, "load_map");
        root.put("path", Objects.requireNonNull(path, "path"));
        return writeSingleLine(root);
    }

    public String encodeCalculate(String id, WorkerPoint pointA, WorkerPoint pointB, double speedMps) {
        ObjectNode root = base(id, "calculate");
        root.set("pointA", pointNode(pointA));
        root.set("pointB", pointNode(pointB));
        if (speedMps == Math.rint(speedMps)) {
            root.put("speedMps", (long) speedMps);
        } else {
            root.put("speedMps", speedMps);
        }
        return writeSingleLine(root);
    }

    public String encodeShutdown(String id) {
        return writeSingleLine(base(id, "shutdown"));
    }

    private ObjectNode base(String id, String operation) {
        if (id == null || id.isEmpty()) {
            throw new IllegalArgumentException("id 必须为非空字符串");
        }
        ObjectNode root = mapper.createObjectNode();
        root.put("id", id);
        root.put("protocolVersion", 1);
        root.put("operation", operation);
        return root;
    }

    private ObjectNode pointNode(WorkerPoint point) {
        ObjectNode node = mapper.createObjectNode();
        if (point instanceof WorkerPoint.Wgs84 w) {
            node.put("type", "wgs84");
            node.put("longitude", w.longitude());
            node.put("latitude", w.latitude());
        } else if (point instanceof WorkerPoint.MapCrs m) {
            node.put("type", "map_crs");
            node.put("x", m.x());
            node.put("y", m.y());
        } else if (point instanceof WorkerPoint.Pixel p) {
            node.put("type", "pixel");
            node.put("column", p.column());
            node.put("row", p.row());
        } else {
            throw new IllegalArgumentException("未知坐标类型: " + point.getClass());
        }
        return node;
    }

    private String writeSingleLine(ObjectNode root) {
        try {
            String json = mapper.writeValueAsString(root);
            if (json.indexOf('\n') >= 0 || json.indexOf('\r') >= 0) {
                throw new WorkerProtocolException("编码结果必须为单行 JSON");
            }
            return json;
        } catch (WorkerProtocolException e) {
            throw e;
        } catch (Exception e) {
            throw new WorkerProtocolException("请求编码失败", e);
        }
    }

    /**
     * 解码一行响应并严格校验信封；任何不符均抛 WorkerProtocolException。
     * 未知附加字段允许存在。
     */
    public WorkerResponse decode(String line, String expectedId) {
        Objects.requireNonNull(line, "line");
        Objects.requireNonNull(expectedId, "expectedId");
        final JsonNode root;
        try {
            root = mapper.readTree(line);
        } catch (Exception e) {
            throw new WorkerProtocolException("响应不是有效 JSON: " + e.getMessage(), e);
        }
        if (root == null || !root.isObject()) {
            throw new WorkerProtocolException("响应根节点必须是 JSON 对象");
        }
        JsonNode idNode = root.get("id");
        if (idNode == null || !idNode.isTextual()) {
            throw new WorkerProtocolException("响应缺少字符串 id");
        }
        String id = idNode.asText();
        if (!id.equals(expectedId)) {
            throw new WorkerProtocolException(
                    "响应 id 与请求不一致: expected=" + expectedId + " actual=" + id);
        }
        JsonNode successNode = root.get("success");
        if (successNode == null || !successNode.isBoolean()) {
            throw new WorkerProtocolException("响应 success 必须是 JSON boolean");
        }
        boolean success = successNode.asBoolean();
        JsonNode data = root.get("data");
        JsonNode error = root.get("error");
        if (success) {
            if (error != null) {
                throw new WorkerProtocolException("成功响应不得包含 error");
            }
            if (data == null || !data.isObject()) {
                throw new WorkerProtocolException("成功响应必须包含对象 data");
            }
            return new WorkerResponse(true, id, data, null, null);
        }
        if (data != null) {
            throw new WorkerProtocolException("失败响应不得包含 data");
        }
        if (error == null || !error.isObject()) {
            throw new WorkerProtocolException("失败响应必须包含对象 error");
        }
        JsonNode code = error.get("code");
        JsonNode message = error.get("message");
        if (code == null || !code.isTextual() || message == null || !message.isTextual()) {
            throw new WorkerProtocolException("error 必须包含字符串 code 和 message");
        }
        return new WorkerResponse(false, id, null, code.asText(), message.asText());
    }

    public record WorkerResponse(boolean success, String id, JsonNode data,
                                 String errorCode, String errorMessage) {
    }
}
