package com.drone.worker;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class NdjsonCodecTest {

    private final NdjsonCodec codec = new NdjsonCodec();
    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void encodeHelloFields() throws Exception {
        String line = codec.encodeHello("h-1");
        JsonNode n = mapper.readTree(line);
        assertEquals("h-1", n.path("id").asText());
        assertEquals(1, n.path("protocolVersion").asInt());
        assertEquals("hello", n.path("operation").asText());
    }

    @Test
    void encodeLoadMapFieldsAndChinesePath() throws Exception {
        String line = codec.encodeLoadMap("m-1", "D:\\地图 数据\\main.tif");
        JsonNode n = mapper.readTree(line);
        assertEquals("load_map", n.path("operation").asText());
        assertEquals("D:\\地图 数据\\main.tif", n.path("path").asText());
        assertTrue(line.contains("地图 数据"));
    }

    @Test
    void encodeCalculateThreePointTypes() throws Exception {
        String line = codec.encodeCalculate("c-1",
                new WorkerPoint.Wgs84(104.123456, 30.654321),
                new WorkerPoint.Pixel(182.5, 94.5),
                10);
        JsonNode n = mapper.readTree(line);
        assertEquals("calculate", n.path("operation").asText());
        assertEquals(10, n.path("speedMps").asInt());
        JsonNode a = n.path("pointA");
        assertEquals("wgs84", a.path("type").asText());
        assertEquals(104.123456, a.path("longitude").asDouble(), 1e-12);
        assertEquals(30.654321, a.path("latitude").asDouble(), 1e-12);
        JsonNode b = n.path("pointB");
        assertEquals("pixel", b.path("type").asText());
        assertEquals(182.5, b.path("column").asDouble(), 1e-12);
        assertEquals(94.5, b.path("row").asDouble(), 1e-12);

        String line2 = codec.encodeCalculate("c-2",
                new WorkerPoint.MapCrs(11590732.5, 3589123.75),
                new WorkerPoint.Wgs84(1.0, 2.0),
                99);
        JsonNode n2 = mapper.readTree(line2);
        assertEquals("map_crs", n2.path("pointA").path("type").asText());
        assertEquals(11590732.5, n2.path("pointA").path("x").asDouble(), 1e-9);
        assertEquals(3589123.75, n2.path("pointA").path("y").asDouble(), 1e-9);
    }

    @Test
    void encodeShutdownFields() throws Exception {
        JsonNode n = mapper.readTree(codec.encodeShutdown("s-1"));
        assertEquals("shutdown", n.path("operation").asText());
    }

    @Test
    void encodedLinesAreSingleLineWithoutCrLf() {
        assertTrue(codec.encodeHello("h-1").indexOf('\n') < 0);
        assertTrue(codec.encodeHello("h-1").indexOf('\r') < 0);
        assertTrue(codec.encodeLoadMap("m-1", "中文路径/a.tif").indexOf('\n') < 0);
    }

    @Test
    void decodeSuccessEnvelope() {
        NdjsonCodec.WorkerResponse r = codec.decode(
                "{\"id\":\"h-1\",\"success\":true,\"data\":{\"protocolVersion\":1}}", "h-1");
        assertTrue(r.success());
        assertEquals("h-1", r.id());
        assertEquals(1, r.data().path("protocolVersion").asInt());
        assertNull(r.errorCode());
    }

    @Test
    void decodeBusinessFailureEnvelope() {
        NdjsonCodec.WorkerResponse r = codec.decode(
                "{\"id\":\"c-1\",\"success\":false,\"error\":{\"code\":\"E_SPEED_INVALID\",\"message\":\"bad\"}}",
                "c-1");
        assertFalse(r.success());
        assertEquals("E_SPEED_INVALID", r.errorCode());
        assertEquals("bad", r.errorMessage());
        assertNull(r.data());
    }

    @Test
    void decodeAllowsUnknownExtraFields() {
        NdjsonCodec.WorkerResponse r = codec.decode(
                "{\"id\":\"h-1\",\"success\":true,\"data\":{},\"extra\":123}", "h-1");
        assertTrue(r.success());
        assertTrue(r.data().isObject());
    }

    @Test
    void decodeRejectsNonJson() {
        assertThrows(WorkerProtocolException.class, () -> codec.decode("not json", "h-1"));
        assertThrows(WorkerProtocolException.class, () -> codec.decode("   ", "h-1"));
        assertThrows(WorkerProtocolException.class, () -> codec.decode("null", "h-1"));
    }

    @Test
    void decodeRejectsArrayRoot() {
        assertThrows(WorkerProtocolException.class,
                () -> codec.decode("[1,2,3]", "h-1"));
    }

    @Test
    void decodeRejectsMissingIdAndMismatch() {
        assertThrows(WorkerProtocolException.class,
                () -> codec.decode("{\"success\":true,\"data\":{}}", "h-1"));
        assertThrows(WorkerProtocolException.class,
                () -> codec.decode("{\"id\":123,\"success\":true,\"data\":{}}", "h-1"));
        assertThrows(WorkerProtocolException.class,
                () -> codec.decode("{\"id\":\"other\",\"success\":true,\"data\":{}}", "h-1"));
    }

    @Test
    void decodeRejectsBadSuccessType() {
        assertThrows(WorkerProtocolException.class,
                () -> codec.decode("{\"id\":\"h-1\",\"success\":\"true\",\"data\":{}}", "h-1"));
    }

    @Test
    void decodeRejectsDataAndErrorTogetherOrMissing() {
        assertThrows(WorkerProtocolException.class,
                () -> codec.decode(
                        "{\"id\":\"h-1\",\"success\":true,\"data\":{},\"error\":{}}", "h-1"));
        assertThrows(WorkerProtocolException.class,
                () -> codec.decode("{\"id\":\"h-1\",\"success\":true}", "h-1"));
        assertThrows(WorkerProtocolException.class,
                () -> codec.decode(
                        "{\"id\":\"h-1\",\"success\":false,\"error\":{\"code\":1,\"message\":\"x\"}}", "h-1"));
    }
}
