package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// ====================================================
//  资产结构体
// ====================================================

// Drone 无人机注册信息
type Drone struct {
	DroneID    string `json:"droneId"`
	Model      string `json:"model"`      // 型号
	OwnerOrg   string `json:"ownerOrg"`   // 所属组织
	Registered string `json:"registered"` // 注册时间 RFC3339
	Status     string `json:"status"`     // active / maintenance / retired
}

// TrackRecord 单条飞行轨迹点
type TrackRecord struct {
	DroneID    string  `json:"droneId"`
	Latitude   float64 `json:"latitude"`
	Longitude  float64 `json:"longitude"`
	Altitude   float64 `json:"altitude"`
	Speed      float64 `json:"speed"`      // m/s
	Battery    int     `json:"battery"`    // 电量百分比
	PilotID    string  `json:"pilotId"`    // 飞手 ID
	RecordedAt string  `json:"recordedAt"` // 飞控时间 RFC3339
}

// Maintenance 维保记录
type Maintenance struct {
	RecordID    string `json:"recordId"`
	DroneID     string `json:"droneId"`
	Type        string `json:"type"`        // inspection / repair / part_replacement
	Description string `json:"description"`  // 维保描述
	Technician  string `json:"technician"`   // 维保人员
	PartChanged string `json:"partChanged"`  // 更换零件（无则为空）
	RecordedAt  string `json:"recordedAt"`   // 维保时间 RFC3339
}

// ====================================================
//  合约主体
// ====================================================

type SmartContract struct {
	contractapi.Contract
}

// ====================================================
//  辅助函数
// ====================================================

// getClientOrg 从证书中提取调用者所属组织
func (s *SmartContract) getClientOrg(ctx contractapi.TransactionContextInterface) (string, error) {
	cert, err := ctx.GetClientIdentity().GetX509Certificate()
	if err != nil {
		return "", fmt.Errorf("failed to get client certificate: %w", err)
	}
	return cert.Subject.Organization[0], nil
}

// getClientID 获取调用者 CN
func (s *SmartContract) getClientID(ctx contractapi.TransactionContextInterface) (string, error) {
	id, err := ctx.GetClientIdentity().GetID()
	if err != nil {
		return "", fmt.Errorf("failed to get client identity: %w", err)
	}
	return id, nil
}

// requireRole 校验调用者组织权限
func (s *SmartContract) requireRole(ctx contractapi.TransactionContextInterface, allowedOrgs ...string) error {
	org, err := s.getClientOrg(ctx)
	if err != nil {
		return err
	}
	for _, allowed := range allowedOrgs {
		if org == allowed {
			return nil
		}
	}
	return fmt.Errorf("org '%s' is not authorized for this operation", org)
}

// ====================================================
//  无人机注册
// ====================================================

// RegisterDrone 注册新无人机（仅管理员）
func (s *SmartContract) RegisterDrone(ctx contractapi.TransactionContextInterface,
	droneID string, model string, ownerOrg string) error {

	if err := s.requireRole(ctx, "AdminOrg"); err != nil {
		return err
	}
	if droneID == "" {
		return errors.New("droneId is required")
	}

	exists, err := s.DroneExists(ctx, droneID)
	if err != nil {
		return fmt.Errorf("failed to check drone: %w", err)
	}
	if exists {
		return fmt.Errorf("drone %s already registered", droneID)
	}

	drone := Drone{
		DroneID:    droneID,
		Model:      model,
		OwnerOrg:   ownerOrg,
		Registered: time.Now().UTC().Format(time.RFC3339),
		Status:     "active",
	}

	droneJSON, err := json.Marshal(drone)
	if err != nil {
		return fmt.Errorf("failed to marshal drone: %w", err)
	}

	if err := ctx.GetStub().PutState(droneID, droneJSON); err != nil {
		return fmt.Errorf("failed to put drone state: %w", err)
	}

	return ctx.GetStub().SetEvent("DroneRegistered", droneJSON)
}

// DroneExists 检查无人机是否已注册
func (s *SmartContract) DroneExists(ctx contractapi.TransactionContextInterface, droneID string) (bool, error) {
	data, err := ctx.GetStub().GetState(droneID)
	if err != nil {
		return false, fmt.Errorf("failed to get drone state: %w", err)
	}
	return data != nil, nil
}

// ReadDrone 查询无人机注册信息
func (s *SmartContract) ReadDrone(ctx contractapi.TransactionContextInterface, droneID string) (*Drone, error) {
	data, err := ctx.GetStub().GetState(droneID)
	if err != nil {
		return nil, fmt.Errorf("failed to get drone state: %w", err)
	}
	if data == nil {
		return nil, fmt.Errorf("drone %s not found", droneID)
	}

	var drone Drone
	if err := json.Unmarshal(data, &drone); err != nil {
		return nil, fmt.Errorf("failed to unmarshal drone: %w", err)
	}
	return &drone, nil
}

// ====================================================
//  飞行轨迹记录（Append-Only 模式）
// ====================================================

// RecordTrack 追加一条飞行轨迹点（仅飞手）
func (s *SmartContract) RecordTrack(ctx contractapi.TransactionContextInterface,
	droneID string, pilotID string,
	latitude float64, longitude float64, altitude float64,
	speed float64, battery int, recordedAt string) error {

	if err := s.requireRole(ctx, "PilotOrg", "AdminOrg"); err != nil {
		return err
	}

	// 校验无人机存在
	exists, err := s.DroneExists(ctx, droneID)
	if err != nil {
		return err
	}
	if !exists {
		return fmt.Errorf("drone %s not registered", droneID)
	}

	// 构造轨迹记录
	track := TrackRecord{
		DroneID:    droneID,
		Latitude:   latitude,
		Longitude:  longitude,
		Altitude:   altitude,
		Speed:      speed,
		Battery:    battery,
		PilotID:    pilotID,
		RecordedAt: recordedAt,
	}

	trackJSON, err := json.Marshal(track)
	if err != nil {
		return fmt.Errorf("failed to marshal track record: %w", err)
	}

	// 使用复合键存储，格式：track~droneID~timestamp
	// 每条轨迹点独立存储，永不覆盖
	key, err := ctx.GetStub().CreateCompositeKey("track", []string{droneID, recordedAt})
	if err != nil {
		return fmt.Errorf("failed to create composite key: %w", err)
	}

	if err := ctx.GetStub().PutState(key, trackJSON); err != nil {
		return fmt.Errorf("failed to put track state: %w", err)
	}

	// 发射事件通知 Python 后端（WebSocket / MQTT 消费者能实时监听到）
	return ctx.GetStub().SetEvent("TrackRecorded", trackJSON)
}

// QueryTracksByDrone 按无人机 ID 查询所有轨迹点（带时间范围可选）
func (s *SmartContract) QueryTracksByDrone(ctx contractapi.TransactionContextInterface,
	droneID string, fromTime string, toTime string) ([]*TrackRecord, error) {

	// 构造范围查询的起止键
	startKey, err := ctx.GetStub().CreateCompositeKey("track", []string{droneID, fromTime})
	if err != nil {
		return nil, fmt.Errorf("failed to create start key: %w", err)
	}
	endKey, err := ctx.GetStub().CreateCompositeKey("track", []string{droneID, toTime + "\uffff"})
	if err != nil {
		return nil, fmt.Errorf("failed to create end key: %w", err)
	}

	iterator, err := ctx.GetStub().GetStateByRange(startKey, endKey)
	if err != nil {
		return nil, fmt.Errorf("failed to get state by range: %w", err)
	}
	defer iterator.Close()

	var tracks []*TrackRecord
	for iterator.HasNext() {
		kv, err := iterator.Next()
		if err != nil {
			return nil, fmt.Errorf("iterator error: %w", err)
		}
		var track TrackRecord
		if err := json.Unmarshal(kv.Value, &track); err != nil {
			return nil, fmt.Errorf("failed to unmarshal track: %w", err)
		}
		tracks = append(tracks, &track)
	}

	return tracks, nil
}

// GetTrackHistory 获取一条轨迹键的历史修改记录（用于审计追溯）
// 注意：因为轨迹是 Append-Only 模式，history 通常只有一条。
// 此函数更多用在无人机注册信息的变更追溯上。
func (s *SmartContract) GetTrackHistory(ctx contractapi.TransactionContextInterface, key string) (string, error) {
	iterator, err := ctx.GetStub().GetHistoryForKey(key)
	if err != nil {
		return "", fmt.Errorf("failed to get history: %w", err)
	}
	defer iterator.Close()

	var records []map[string]interface{}
	for iterator.HasNext() {
		item, err := iterator.Next()
		if err != nil {
			return "", fmt.Errorf("history iterator error: %w", err)
		}
		records = append(records, map[string]interface{}{
			"txId":      item.TxId,
			"timestamp": time.Unix(item.Timestamp.GetSeconds(), 0).UTC().Format(time.RFC3339),
			"isDelete":  item.IsDelete,
			"value":     string(item.Value),
		})
	}

	historyJSON, err := json.Marshal(records)
	if err != nil {
		return "", fmt.Errorf("failed to marshal history: %w", err)
	}

	return string(historyJSON), nil
}

// ====================================================
//  维保记录
// ====================================================

// RecordMaintenance 记录一次维保操作
func (s *SmartContract) RecordMaintenance(ctx contractapi.TransactionContextInterface,
	recordID string, droneID string, maintType string,
	description string, technician string, partChanged string, recordedAt string) error {

	if err := s.requireRole(ctx, "MaintenanceOrg", "AdminOrg"); err != nil {
		return err
	}

	maintenance := Maintenance{
		RecordID:    recordID,
		DroneID:     droneID,
		Type:        maintType,
		Description: description,
		Technician:  technician,
		PartChanged: partChanged,
		RecordedAt:  recordedAt,
	}

	maintJSON, err := json.Marshal(maintenance)
	if err != nil {
		return fmt.Errorf("failed to marshal maintenance: %w", err)
	}

	// 复合键：maint~droneID~recordID，按无人机 + 时间排序
	key, err := ctx.GetStub().CreateCompositeKey("maint", []string{droneID, recordID})
	if err != nil {
		return fmt.Errorf("failed to create composite key: %w", err)
	}

	if err := ctx.GetStub().PutState(key, maintJSON); err != nil {
		return fmt.Errorf("failed to put maintenance state: %w", err)
	}

	return ctx.GetStub().SetEvent("MaintenanceRecorded", maintJSON)
}

// QueryMaintenanceByDrone 查询某架无人机的全部维保记录
func (s *SmartContract) QueryMaintenanceByDrone(ctx contractapi.TransactionContextInterface,
	droneID string) ([]*Maintenance, error) {

	iterator, err := ctx.GetStub().GetStateByPartialCompositeKey("maint", []string{droneID})
	if err != nil {
		return nil, fmt.Errorf("failed to get maintenance iterator: %w", err)
	}
	defer iterator.Close()

	var records []*Maintenance
	for iterator.HasNext() {
		kv, err := iterator.Next()
		if err != nil {
			return nil, fmt.Errorf("maintenance iterator error: %w", err)
		}
		var m Maintenance
		if err := json.Unmarshal(kv.Value, &m); err != nil {
			return nil, fmt.Errorf("failed to unmarshal maintenance: %w", err)
		}
		records = append(records, &m)
	}

	return records, nil
}

// ====================================================
//  启动入口
// ====================================================

func main() {
	chaincode, err := contractapi.NewChaincode(&SmartContract{})
	if err != nil {
		fmt.Printf("Error creating chaincode: %s\n", err)
		return
	}

	if err := chaincode.Start(); err != nil {
		fmt.Printf("Error starting chaincode: %s\n", err)
	}
}
