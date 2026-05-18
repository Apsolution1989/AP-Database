import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ตั้งค่าหน้าจอ
st.set_page_config(page_title="Material Cost Tracker", layout="centered")
st.title("AP Solution(1989) Co.,Ltd.")
st.subheader("ระบบบริหารจัดการฐานข้อมูลวัสดุ")

# เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# ส่วนของการเลือกเมนูฝั่งซ้ายมือ (อัปเดตตามข้อ 3)
menu = ["Request (ขอวัสดุ)", "บันทึกข้อมูล (Supplier/ราคา)", "เรียกดูข้อมูลทั้งหมด"]
choice = st.sidebar.selectbox("เมนูระบบ", menu)

# ====================================================================
# เมนูที่ 1: หน้าสำหรับเปิด Request (อัปเดตตามข้อ 4)
# ====================================================================
if choice == "Request (ขอวัสดุ)":
    st.markdown("### 📝 สร้างรายการขอวัสดุใหม่ (Material Request)")
    
    with st.form(key="request_form"):
        type_val = st.selectbox("ประเภทวัสดุ", ["Piping", "Electrical", "Structural", "Other"])
        project_val = st.text_input("ชื่อโครงการ (Project Name)")
        request_val = st.text_area("รายการวัสดุที่ต้องการ (Material Request)")
        
        submit_req = st.form_submit_button(label="บันทึกใบขอวัสดุ")

    if submit_req:
        if not project_val or not request_val:
            st.error("❌ กรุณากรอกชื่อ Project และรายละเอียด Material Request ให้ครบถ้วน")
        else:
            # เตรียมข้อมูลโครงร่าง (Supplier Detail และ Price จะถูกปล่อยว่างไว้ก่อนในขั้นตอนนี้)
            new_req = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Type": type_val,
                "Project": project_val,
                "Material Request": request_val,
                "Supplier Detail": "-", # ใส่ค่าตั้งต้นไว้รอ
                "Price": 0.0            # ใส่ราคาตั้งต้นเป็น 0
            }])
            
            # ดึงข้อมูลเดิมและบันทึกต่อท้ายเข้าไป
            existing_data = conn.read(worksheet="Sheet1", ttl=0)
            updated_df = pd.concat([existing_data, new_req], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            
            st.success(f"🎉 บันทึกรายการขอวัสดุสำหรับโครงการ '{project_val}' เรียบร้อยแล้ว! กรุณาไปที่เมนูถัดไปเพื่อลงรายละเอียดราคา")
            st.rerun()

# ====================================================================
# เมนูที่ 2: หน้าสำหรับอัปเดตข้อมูล Supplier และ ราคา (อัปเดตตามข้อ 5)
# ====================================================================
elif choice == "บันทึกข้อมูล (Supplier/ราคา)":
    st.markdown("### 🏷️ อัปเดตข้อมูลซัพพลายเออร์และราคาวัสดุ")
    
    # ดึงข้อมูลทั้งหมดจากชีตมาแสดงก่อน
    data = conn.read(worksheet="Sheet1", ttl=0)
    
    if not data.empty and "Material Request" in data.columns:
        # กรองหาเฉพาะแถวที่ยังไม่มีข้อมูล Supplier หรือ ราคายังเป็น 0 (แปลว่าเพิ่งสร้างมาจากหน้า Request)
        pending_data = data[(data["Supplier Detail"] == "-") | (data["Price"] == 0)]
        
        if pending_data.empty:
            st.info("✅ ไม่มีรายการค้างบันทึกราคาในระบบขณะนี้")
        else:
            st.write("เลือกรายการ Request ที่คุณต้องการนำมาลงราคา:")
            
            # สร้างตัวเลือกแสดงผลให้ผู้ใช้จดจำง่าย [ชื่อโครงการ - รายการวัสดุ]
            pending_list = pending_data.apply(lambda r: f"[{r['Project']}] {r['Material Request'][:30]}...", axis=1).tolist()
            selected_option = st.selectbox("รายการที่ค้างดำเนินการ", pending_list)
            
            # ดึงดัชนี (Index) จริงในตัวแปร data ของแถวที่ผู้ใช้เลือก
            selected_index = pending_data.index[pending_list.index(selected_option)]
            row_info = data.loc[selected_index]
            
            # แสดงข้อมูลเดิมที่กรอกมาจากหน้า Request ให้ผู้ใช้เห็นเพื่อความแม่นยำ
            st.info(f"📋 **รายละเอียดงานที่กำลังลงราคา:**\n* **โครงการ:** {row_info['Project']}\n* **วัสดุที่ขอ:** {row_info['Material Request']}")
            
            # ฟอร์มสำหรับให้กรอกข้อมูลเพิ่มเติม (Supplier & Price)
            with st.form(key="supplier_form"):
                supplier_val = st.text_area("รายละเอียดผู้ขาย / สเปกเพิ่มเติม (Supplier Detail)")
                price_val = st.number_input("ยอดราคาสุทธิ (บาท)", min_value=0.0, format="%.2f")
                
                submit_supplier = st.form_submit_button(label="อัปเดตข้อมูลราคา")
            
            if submit_supplier:
                if not supplier_val or price_val <= 0:
                    st.error("❌ กรุณากรอกรายละเอียด Supplier และระบุราคาที่มากกว่า 0 บาท")
                else:
                    # อัปเดตข้อมูลลงในตำแหน่ง Index เดิมของตารางนั้นๆ
                    data.at[selected_index, "Supplier Detail"] = supplier_val
                    data.at[selected_index, "Price"] = price_val
                    data.at[selected_index, "Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # อัปเดตเวลาล่าสุด
                    
                    # อัปเดตกลับไปยัง Google Sheets ทั้งตาราง
                    conn.update(worksheet="Sheet1", data=data)
                    st.success("💾 อัปเดตข้อมูล Supplier และราคาลงฐานข้อมูลเรียบร้อยแล้ว!")
                    st.rerun()
    else:
        st.warning("⚠️ ไม่พบข้อมูลโครงสร้างตารางหลักในระบบ กรุณาตรวจสอบ Google Sheets")

# ====================================================================
# เมนูที่ 3: หน้าสำหรับเรียกดูข้อมูลและกรองข้อมูล
# ====================================================================
elif choice == "เรียกดูข้อมูลทั้งหมด":
    st.markdown("### 📊 คลังฐานข้อมูลวัสดุทั้งหมด")
    data = conn.read(worksheet="Sheet1", ttl=0)
    
    if not data.empty and "Project" in data.columns:
        # เพิ่มฟิลเตอร์กรองตาม Project เพื่อให้สแกนข้อมูลง่าย
        project_filter = st.multiselect("กรองดูเฉพาะโครงการที่ต้องการ", options=data["Project"].unique())
        if project_filter:
            data = data[data["Project"].isin(project_filter)]
        
        # จัดแสดงตารางข้อมูล
        st.dataframe(data, use_container_width=True)
        
        # สรุปยอดรวมราคาเฉพาะรายการที่ลงราคาแล้ว
        if "Price" in data.columns:
            total_price = pd.to_numeric(data["Price"]).sum()
            st.metric("มูลค่าราคารวมในระบบขณะนี้", f"{total_price:,.2f} บาท")
    else:
        st.warning("⚠️ ไม่พบข้อมูลในแผ่นงาน Google Sheets หรือหัวตารางไม่ถูกต้อง")
