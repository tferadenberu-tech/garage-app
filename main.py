# --- Remaining Python Backend & Flask Routes ---

@app.route("/", methods=["GET"])
def index():
    # User context info
    user = {"name": "Dinberu Tefera", "role": "System Admin / Head of Mechanical Workshop"}
    
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    
    logs = garage_data["maintenance_logs"]
    
    # Optional date filtering
    filtered_logs = logs
    if start_date_str and end_date_str:
        try:
            s_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            e_date = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
            filtered_logs = [
                log for log in logs 
                if log.get("start_time") and s_date <= datetime.strptime(log["start_time"][:10], "%Y-%m-%d") < e_date
            ]
        except:
            pass

    def compute_summary_stats(log_list):
        total_jobs = len(log_list)
        pm_jobs = sum(1 for l in log_list if l.get("maintenance_type") == "PM")
        cm_jobs = sum(1 for l in log_list if l.get("maintenance_type") == "CM")
        inspection_jobs = sum(1 for l in log_list if l.get("maintenance_type") == "Inspection")
        
        total_work_hours = round(sum(l.get("effective_hours", 0.0) for l in log_list), 2)
        
        total_spare_qty = sum(sum(sp.get("qty", 0) for sp in l.get("replaced_spares", [])) for l in log_list)
        total_spares_cost = sum(sum(sp.get("total_cost", 0.0) for sp in l.get("replaced_spares", [])) for l in log_list)
        
        total_battery_qty = sum(l.get("battery_qty", 0) for l in log_list)
        total_battery_cost = sum(l.get("battery_cost", 0.0) for l in log_list)
        
        total_lubrication_qty = sum(l.get("lubrication_qty", 0.0) for l in log_list)
        total_lubrication_cost = sum(l.get("lubrication_cost", 0.0) for l in log_list)
        
        total_tire_qty = sum(l.get("tire_qty", 0) for l in log_list)
        total_tire_cost = sum(l.get("tire_cost", 0.0) for l in log_list)
        
        total_expenditure = total_spares_cost + total_battery_cost + total_lubrication_cost + total_tire_cost
        
        return {
            "total_jobs": total_jobs,
            "pm_jobs": pm_jobs,
            "cm_jobs": cm_jobs,
            "inspection_jobs": inspection_jobs,
            "total_work_hours": total_work_hours,
            "total_spare_qty": total_spare_qty,
            "total_spares_cost": total_spares_cost,
            "total_battery_qty": total_battery_qty,
            "total_battery_cost": total_battery_cost,
            "total_lubrication_qty": total_lubrication_qty,
            "total_lubrication_cost": total_lubrication_cost,
            "total_tire_qty": total_tire_qty,
            "total_tire_cost": total_tire_cost,
            "total_expenditure": total_expenditure
        }

    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    
    weekly_logs = [l for l in logs if l.get("start_time") and datetime.strptime(l["start_time"][:10], "%Y-%m-%d") >= seven_days_ago]
    monthly_logs = [l for l in logs if l.get("start_time") and datetime.strptime(l["start_time"][:10], "%Y-%m-%d") >= thirty_days_ago]
    
    weekly_summary = compute_summary_stats(weekly_logs)
    monthly_summary = compute_summary_stats(monthly_logs)
    
    full_template = HTML_TEMPLATE + """
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Spare Inventory Modal -->
    <div class="modal fade" id="inventoryModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header bg-primary text-white">
                    <h5 class="modal-title fw-bold">⚙️ SteelY R.M.I Spare Parts Inventory</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <table class="table table-bordered table-sm">
                        <thead class="table-dark">
                            <tr>
                                <th>ID</th>
                                <th>Part Name</th>
                                <th>Specification</th>
                                <th>Vehicle Model</th>
                                <th>Available Qty</th>
                                <th>Unit Price (ETB)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for part in inventory %}
                            <tr>
                                <td>{{ part.id }}</td>
                                <td class="fw-bold">{{ part.part_name }}</td>
                                <td>{{ part.spec }}</td>
                                <td>{{ part.for_vehicle }}</td>
                                <td class="fw-bold text-success">{{ part.qty }}</td>
                                <td>{{ "{:,.2f}".format(part.unit_price) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    </div>

</div></div></div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    function addSpareRow() {
        const container = document.getElementById("spare-rows-container");
        const rowHTML = `
            <div class="row g-2 spare-row mb-2 align-items-center">
                <div class="col-md-3">
                    <input type="text" name="spare_name[]" class="form-control form-control-sm" placeholder="Spare Part Name" required>
                </div>
                <div class="col-md-3">
                    <input type="text" name="spare_spec[]" class="form-control form-control-sm" placeholder="Specification" required>
                </div>
                <div class="col-md-1">
                    <input type="number" name="spare_qty[]" class="form-control form-control-sm spare-qty" placeholder="Qty" value="1" min="1" required oninput="calculateRowTotal(this)">
                </div>
                <div class="col-md-2">
                    <input type="number" step="0.01" name="spare_price[]" class="form-control form-control-sm spare-price" placeholder="Unit Price (ETB)" value="0.00" required oninput="calculateRowTotal(this)">
                </div>
                <div class="col-md-2">
                    <span class="small fw-bold text-success row-total-text">0.00 ETB</span>
                </div>
                <div class="col-md-1">
                    <button type="button" class="btn btn-outline-danger btn-sm w-100" onclick="removeSpareRow(this)">✕</button>
                </div>
            </div>`;
        container.insertAdjacentHTML('beforeend', rowHTML);
    }
    function removeSpareRow(btn) {
        btn.closest('.spare-row').remove();
    }
    function calculateRowTotal(element) {
        const row = element.closest('.spare-row');
        const qty = parseFloat(row.querySelector('.spare-qty').value) || 0;
        const price = parseFloat(row.querySelector('.spare-price').value) || 0;
        const total = qty * price;
        row.querySelector('.row-total-text').innerText = total.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + " ETB";
    }
</script>
</body>
</html>
    """
    
    return render_template_string(
        full_template, 
        user=user, 
        weekly=weekly_summary, 
        monthly=monthly_summary, 
        logs=filtered_logs, 
        inventory=garage_data["spare_parts"]
    )

@app.route("/add_work_order", methods=["POST"])
def add_work_order():
    try:
        sn = request.form.get("sn")
        wo_no = request.form.get("wo_no")
        vehicle = request.form.get("vehicle")
        model = request.form.get("model")
        reading_val = int(request.form.get("reading_value", 0))
        reading_unit = request.form.get("reading_unit", "KM")
        maintenance_type = request.form.get("maintenance_type", "PM")
        work_status = request.form.get("work_status", "Completed")
        driver = request.form.get("driver")
        technicians = request.form.get("technicians")
        start_time = request.form.get("start_time")
        finish_time = request.form.get("finish_time")
        description = request.form.get("description")
        
        effective_hours = calculate_effective_hours(start_time, finish_time)
        next_service_str = calculate_next_service(reading_val, reading_unit)
        
        # Parse Dynamic Spare Parts Rows
        spare_names = request.form.getlist("spare_name[]")
        spare_specs = request.form.getlist("spare_spec[]")
        spare_qtys = request.form.getlist("spare_qty[]")
        spare_prices = request.form.getlist("spare_price[]")
        
        replaced_spares = []
        for i in range(len(spare_names)):
            if spare_names[i].strip():
                q = int(spare_qtys[i]) if i < len(spare_qtys) and spare_qtys[i] else 1
                p = float(spare_prices[i]) if i < len(spare_prices) and spare_prices[i] else 0.0
                replaced_spares.append({
                    "part_name": spare_names[i],
                    "spec": spare_specs[i] if i < len(spare_specs) else "",
                    "qty": q,
                    "unit_price": p,
                    "total_cost": q * p
                })
        
        battery_qty = int(request.form.get("battery_qty", 0) or 0)
        battery_cost = float(request.form.get("battery_cost", 0.0) or 0.0)
        lubrication_qty = float(request.form.get("lubrication_qty", 0.0) or 0.0)
        lubrication_cost = float(request.form.get("lubrication_cost", 0.0) or 0.0)
        tire_qty = int(request.form.get("tire_qty", 0) or 0)
        tire_cost = float(request.form.get("tire_cost", 0.0) or 0.0)
        
        new_log = {
            "id": len(garage_data["maintenance_logs"]) + 1,
            "sn": sn,
            "wo_no": wo_no,
            "vehicle": vehicle,
            "model": model,
            "reading_value": reading_val,
            "reading_unit": reading_unit,
            "next_service": next_service_str,
            "driver": driver,
            "technicians": technicians,
            "maintenance_type": maintenance_type,
            "work_status": work_status,
            "start_time": start_time.replace("T", " ") if start_time else "",
            "finish_time": finish_time.replace("T", " ") if finish_time else "",
            "effective_hours": effective_hours,
            "description": description,
            "replaced_spares": replaced_spares,
            "battery_qty": battery_qty,
            "battery_cost": battery_cost,
            "lubrication_qty": lubrication_qty,
            "lubrication_cost": lubrication_cost,
            "tire_qty": tire_qty,
            "tire_cost": tire_cost
        }
        
        garage_data["maintenance_logs"].insert(0, new_log)
    except Exception as e:
        print(f"Error adding work order: {e}")
        
    return redirect(url_for("index"))

@app.route("/export/master_excel")
@app.route("/export/execution_excel")
def export_excel():
    logs = garage_data["maintenance_logs"]
    flat_data = []
    for log in logs:
        flat_data.append({
            "Serial No": log.get("sn"),
            "Work Order #": log.get("wo_no"),
            "Vehicle Plate": log.get("vehicle"),
            "Model": log.get("model"),
            "Current Reading": log.get("reading_value"),
            "Reading Unit": log.get("reading_unit"),
            "Next Service Alert": log.get("next_service"),
            "Maintenance Type": log.get("maintenance_type"),
            "Status": log.get("work_status"),
            "Technicians": log.get("technicians"),
            "Start Time": log.get("start_time"),
            "Finish Time": log.get("finish_time"),
            "Effective Hours": log.get("effective_hours"),
            "Battery Cost (ETB)": log.get("battery_cost"),
            "Lubrication Cost (ETB)": log.get("lubrication_cost"),
            "Tire Cost (ETB)": log.get("tire_cost")
        })
    
    df = pd.DataFrame(flat_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Maintenance Logs")
    output.seek(0)
    
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"SteelY_Garage_Master_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    )

@app.route("/reset_all_logs")
def reset_all_logs():
    garage_data["maintenance_logs"] = []
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
