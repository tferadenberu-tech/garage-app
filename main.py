# Parse Dynamic Spare Parts Rows & Deduct from Inventory
        spare_names = request.form.getlist("spare_name[]")
        spare_specs = request.form.getlist("spare_spec[]")
        spare_qtys = request.form.getlist("spare_qty[]")
        spare_prices = request.form.getlist("spare_price[]")
        
        replaced_spares = []
        for i in range(len(spare_names)):
            if spare_names[i].strip():
                q = int(spare_qtys[i]) if i < len(spare_qtys) and spare_qtys[i] else 1
                p = float(spare_prices[i]) if i < len(spare_prices) and spare_prices[i] else 0.0
                part_name = spare_names[i].strip()
                
                # Check and deduct from global garage inventory if it exists
                for inv_item in garage_data["spare_parts"]:
                    if inv_item["part_name"].lower() == part_name.lower():
                        inv_item["qty"] = max(0, inv_item["qty"] - q)
                        break

                replaced_spares.append({
                    "part_name": part_name,
                    "spec": spare_specs[i] if i < len(spare_specs) else "",
                    "qty": q,
                    "unit_price": p,
                    "total_cost": q * p
                })
