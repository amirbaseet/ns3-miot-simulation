#!/bin/bash
# ============================================================
# Adds ns-3 energy model to cluster-aodv-nosink.cc
# Run from: ~/projects/ns3-miot-simulation
# ============================================================

FILE="src/wsn/cluster-aodv-nosink.cc"

echo "=== Step 1: Add energy module includes ==="
# Add after the last existing include (ns3/netanim-module.h)
sed -i 's|#include "ns3/netanim-module.h"|#include "ns3/netanim-module.h"\n#include "ns3/energy-module.h"\n#include "ns3/wifi-radio-energy-model-helper.h"|' "$FILE"
echo "[OK] includes added"

echo "=== Step 2: Add EnergySourceContainer declarations before FlowMonitor ==="
# Insert energy setup block before "FlowMonitorHelper fh;"
# The anchor is the unique line:  FlowMonitorHelper fh;
ENERGY_BLOCK='  \/\/ ---- Energy Model Setup ----\n  EnergySourceHelper energySourceHelper;\n  energySourceHelper.SetType ("ns3::BasicEnergySource",\n    "BasicEnergySourceInitialEnergy", DoubleValue (2.0));\n  EnergySourceContainer sensSources;\n  for (uint32_t i = 0; i < numRegular; i++)\n    {\n      NodeContainer tmp;\n      tmp.Add (sens.Get (i));\n      sensSources.Add (energySourceHelper.Install (tmp));\n    }\n\n  EnergySourceHelper chEnergyHelper;\n  chEnergyHelper.SetType ("ns3::BasicEnergySource",\n    "BasicEnergySourceInitialEnergy", DoubleValue (5.0));\n  EnergySourceContainer chSources;\n  for (uint32_t i = 0; i < numCH; i++)\n    {\n      NodeContainer tmp;\n      tmp.Add (chs.Get (i));\n      chSources.Add (chEnergyHelper.Install (tmp));\n    }\n\n  WifiRadioEnergyModelHelper radioEnergyHelper;\n  radioEnergyHelper.Set ("TxCurrentA", DoubleValue (0.380));\n  radioEnergyHelper.Set ("RxCurrentA", DoubleValue (0.313));\n  radioEnergyHelper.Set ("IdleCurrentA", DoubleValue (0.273));\n  radioEnergyHelper.Set ("SleepCurrentA", DoubleValue (0.030));\n  for (uint32_t i = 0; i < numRegular; i++)\n    {\n      NetDeviceContainer d; d.Add (dev.Get (i));\n      radioEnergyHelper.Install (d, sensSources.Get (i));\n    }\n  for (uint32_t i = 0; i < numCH; i++)\n    {\n      NetDeviceContainer d; d.Add (dev.Get (numRegular + i));\n      radioEnergyHelper.Install (d, chSources.Get (i));\n    }\n  std::cout << "  Energy: Sensors=2.0J, CHs=5.0J\\n\\n";\n\n'

sed -i "s|  FlowMonitorHelper fh;|${ENERGY_BLOCK}  FlowMonitorHelper fh;|" "$FILE"
echo "[OK] energy setup block inserted"

echo "=== Step 3: Add energy report and CSV after PrintResults call ==="
# The anchor is the unique block after PrintResults:  // Print CH forwarding stats
ENERGY_REPORT='  \/\/ ---- Energy Report ----\n  std::cout << "  ============================================\\n"\n            << "  ENERGY REPORT\\n"\n            << "  ============================================\\n";\n  double totalSensInit = numRegular * 2.0;\n  double totalCHInit   = numCH * 5.0;\n  double totalSensRemain = 0, totalCHRemain = 0;\n  uint32_t deadSensors = 0, deadCHs = 0;\n  double minSE = 999, maxSE = 0, sumSE = 0;\n  for (uint32_t i = 0; i < numRegular; i++)\n    {\n      double r = sensSources.Get (i)->GetRemainingEnergy ();\n      totalSensRemain += r; sumSE += r;\n      if (r < minSE) minSE = r; if (r > maxSE) maxSE = r;\n      if (r <= 0.0) deadSensors++;\n    }\n  double minCE = 999, maxCE = 0, sumCE = 0;\n  for (uint32_t i = 0; i < numCH; i++)\n    {\n      double r = chSources.Get (i)->GetRemainingEnergy ();\n      totalCHRemain += r; sumCE += r;\n      if (r < minCE) minCE = r; if (r > maxCE) maxCE = r;\n      if (r <= 0.0) deadCHs++;\n    }\n  double sensConsumed = totalSensInit - totalSensRemain;\n  double chConsumed   = totalCHInit   - totalCHRemain;\n  std::cout << std::fixed << std::setprecision (4)\n            << "  Sensor Energy:\\n"\n            << "    Initial: "   << totalSensInit   << " J (" << numRegular << " x 2.0 J)\\n"\n            << "    Remaining: " << totalSensRemain << " J\\n"\n            << "    Consumed: "  << sensConsumed    << " J ("\n            << std::setprecision (1) << (sensConsumed\/totalSensInit*100) << "%)\\n"\n            << std::setprecision (4)\n            << "    Per sensor: avg=" << (numRegular>0?sumSE\/numRegular:0)\n            << "J  min=" << minSE << "J  max=" << maxSE << "J\\n"\n            << "    Dead sensors (0 energy): " << deadSensors << "\\n"\n            << "  CH Energy:\\n"\n            << "    Initial: "   << totalCHInit   << " J (" << numCH << " x 5.0 J)\\n"\n            << "    Remaining: " << totalCHRemain << " J\\n"\n            << "    Consumed: "  << chConsumed    << " J ("\n            << std::setprecision (1) << (chConsumed\/totalCHInit*100) << "%)\\n"\n            << std::setprecision (4)\n            << "    Per CH: avg=" << (numCH>0?sumCE\/numCH:0)\n            << "J  min=" << minCE << "J  max=" << maxCE << "J\\n"\n            << "    Dead CHs (0 energy): " << deadCHs << "\\n"\n            << "  ============================================\\n\\n";\n  std::string energyCsv = csvName + ".energy.csv";\n  std::ofstream ecsv (energyCsv);\n  ecsv << "NodeID,Type,InitialEnergy_J,RemainingEnergy_J,ConsumedEnergy_J,ConsumedPct\\n";\n  uint32_t nECG_e = numRegular\/3, nHR_e = numRegular\/3;\n  for (uint32_t i = 0; i < numRegular; i++)\n    {\n      double rem = sensSources.Get (i)->GetRemainingEnergy ();\n      double cons = 2.0 - rem;\n      std::string t = (i < nECG_e) ? "ECG" : (i < nECG_e+nHR_e) ? "HR" : "Temp";\n      ecsv << i << "," << t << ",2.0," << std::fixed << std::setprecision (4)\n           << rem << "," << cons << "," << std::setprecision (2) << (cons\/2.0*100) << "\\n";\n    }\n  for (uint32_t i = 0; i < numCH; i++)\n    {\n      double rem = chSources.Get (i)->GetRemainingEnergy ();\n      double cons = 5.0 - rem;\n      ecsv << (numRegular+i) << ",CH,5.0," << std::fixed << std::setprecision (4)\n           << rem << "," << cons << "," << std::setprecision (2) << (cons\/5.0*100) << "\\n";\n    }\n  ecsv.close ();\n  std::cout << "  Energy CSV: " << energyCsv << "\\n\\n";\n\n'

sed -i "s|  \/\/ Print CH forwarding stats|${ENERGY_REPORT}  \/\/ Print CH forwarding stats|" "$FILE"
echo "[OK] energy report block inserted"

echo ""
echo "=== Verify key additions ==="
grep -n "energy-module\|EnergySource\|ENERGY REPORT\|energyCsv" "$FILE" | head -12

echo ""
echo "=== Done. Now run: ==="
echo "  cp src/wsn/cluster-aodv-nosink.cc ~/ns-3-dev/scratch/cluster-aodv-nosink/"
echo "  cd ~/ns-3-dev && ./ns3 build 2>&1 | tail -5"
