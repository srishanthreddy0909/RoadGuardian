from integration.risk_wrapper import predict_risk

print("SAFE")
print(predict_risk(0,0,0))

print("MEDIUM")
print(predict_risk(0,1,0))

print("HIGH")
print(predict_risk(1,1,1))
