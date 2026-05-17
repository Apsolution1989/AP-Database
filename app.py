import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ตั้งค่าหน้าจอ
st.set_page_config(page_title="Material Cost Tracker", layout="centered")
st.title("ระบบบันทึกฐานข้อมูลวัสดุ")

# เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# ส่วนของการเลือกเมนู
menu = ["บันทึกข้อมูล", "เรียกดูข้อมูล"]
choice = st.sidebar.selectbox("เมนู", menu)

if choice == "บันทึกข้อมูล":
    st.subheader("กรอกรายละเอียดวัสดุ")
    
    with st.form(key="material_form"):
        type_val = st.selectbox("ประเภทวัสดุ", ["Piping", "Electrical", "Structural", "Other"])
        project_val = st.text_input("Project Name")
        detail_val = st.text_area("Detail วัสดุ")
        price_val = st.number_input("ราคา", min_value=0.0, format="%.2f")
        
        submit_button = st.form_submit_button(label="บันทึกข้อมูล")

    if submit_button:
        # เตรียมข้อมูลใหม่
        new_data = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Type": type_val,
            "Project": project_val,
            "Detail": detail_val,
            "Price": price_val
        }])
        
        # ดึงข้อมูลเดิมมาต่อกับข้อมูลใหม่
        existing_data = conn.read(worksheet="Sheet1")
        updated_df = pd.concat([existing_data, new_data], ignore_index=True)
        
        # อัปเดตกลับไปที่ Google Sheets
        conn.update(worksheet="Sheet1", data=updated_df)
        st.success("บันทึกข้อมูลเรียบร้อยแล้ว!")

elif choice == "เรียกดูข้อมูล":
    st.subheader("ฐานข้อมูลวัสดุทั้งหมด")
    data = conn.read(worksheet="Sheet1")
    
    # เพิ่มฟิลเตอร์กรองตาม Project
    project_filter = st.multiselect("เลือก Project", options=data["Project"].unique())
    if project_filter:
        data = data[data["Project"].isin(project_filter)]
    
    st.dataframe(data, use_container_width=True)
    
    # สรุปยอดรวมราคา
    total_price = data["Price"].sum()
    st.metric("ราคารวมทั้งหมด", f"{total_price:,.2f} บาท")
