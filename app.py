import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ตั้งค่าหน้าจอ
st.set_page_config(page_title="Material Cost Tracker", layout="centered")
st.title("AP Solution(1989) Co.,Ltd.")
st.subheader("ระบบบริหารจัดการฐานข้อมูลวัสดุ (พร้อมระบบแนบไฟล์)")

# เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# เมนูฝั่งซ้ายมือ
menu = ["Request (ขอวัสดุ)", "บันทึกข้อมูล (Supplier/ราคา)", "เรียกดูข้อมูลทั้งหมด"]
choice = st.sidebar.selectbox("เมนูระบบ", menu)

# ====================================================================
# เมนูที่ 1: หน้าสำหรับเปิด Request 
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
            new_req = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Type": type_val,
                "Project": project_val,
                "Material Request": request_val,
                "Supplier Detail": "-",
                "Price": 0.0,
                "Attachment Link": "-" # ตั้งค่าเริ่มต้นไว้ว่างเปล่า
            }])
            
            existing_data = conn.read(worksheet="Sheet1", ttl=0)
            updated_df = pd.concat([existing_data, new_req], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            
            st.success(f"🎉 บันทึกรายการเรียบร้อยแล้ว!")
            st.rerun()

# ====================================================================
# เมนูที่ 2: หน้าสำหรับอัปเดตข้อมูล Supplier, ราคา และไฟล์แนบ (อัปเดตใหม่)
# ====================================================================
elif choice == "บันทึกข้อมูล (Supplier/ราคา)":
    st.markdown("### 🏷️ อัปเดตข้อมูลซัพพลายเออร์ ราคา และหลักฐานแนบ")
    
    data = conn.read(worksheet="Sheet1", ttl=0)
    
    if not data.empty and "Material Request" in data.columns:
        pending_data = data[(data["Supplier Detail"] == "-") | (data["Price"] == 0)]
        
        if pending_data.empty:
            st.info("✅ ไม่มีรายการค้างบันทึกราคาในระบบขณะนี้")
        else:
            st.write("เลือกรายการ Request ที่คุณต้องการนำมาลงราคา:")
            pending_list = pending_data.apply(lambda r: f"[{r['Project']}] {r['Material Request'][:30]}...", axis=1).tolist()
            selected_option = st.selectbox("รายการที่ค้างดำเนินการ", pending_list)
            
            selected_index = pending_data.index[pending_list.index(selected_option)]
            row_info = data.loc[selected_index]
            
            st.info(f"📋 **รายละเอียดงาน:**\n* **โครงการ:** {row_info['Project']}\n* **วัสดุที่ขอ:** {row_info['Material Request']}")
            
            # ฟอร์มกรอกข้อมูลพร้อมระบบแนบรูป/ไฟล์
            with st.form(key="supplier_form"):
                supplier_val = st.text_area("รายละเอียดผู้ขาย / สเปกเพิ่มเติม (Supplier Detail)")
                price_val = st.number_input("ยอดราคาสุทธิ (บาท)", min_value=0.0, format="%.2f")
                
                st.markdown("---")
                st.markdown("📷 **ส่วนของไฟล์แนบ / รูปภาพประกอบ**")
                
                # รูปแบบเติมลิงก์ไฟล์ตรงๆ (เช่น ลิงก์ที่ก๊อปมาจาก Google Drive ของบริษัท)
                file_link_input = st.text_input("วางลิงก์ไฟล์แนบ/รูปถ่าย (เช่น ลิงก์ Google Drive, LINE Album)", value="-")
                
                # หรือเปิดให้เลือกไฟล์จากคอมพิวเตอร์ชั่วคราว
                uploaded_file = st.file_uploader("หรือเลือกอัปโหลดไฟล์/รูปภาพ (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])
                
                submit_supplier = st.form_submit_button(label="อัปเดตข้อมูลและบันทึกไฟล์")
            
            if submit_supplier:
                if not supplier_val or price_val <= 0:
                    st.error("❌ กรุณากรอกรายละเอียด Supplier และระบุราคาให้ถูกต้อง")
                else:
                    final_link = file_link_input
                    
                    # ถัามีการเลือกอัปโหลดไฟล์ผ่านหน้าเว็บเข้ามา
                    if uploaded_file is not None:
                        # 💡 จุดต่อยอด: ส่วนนี้สามารถเขียนคำสั่งส่งไฟล์เข้า Google Drive ได้
                        # ในเบื้องต้นระบบจะบันทึกชื่อไฟล์ไว้ในฐานข้อมูลให้ก่อนเพื่อเป็นหลักฐาน
                        final_link = f"ไฟล์แนบ: {uploaded_file.name} (กรุณาเปิดระบบอัปโหลดคลาวด์)"
                    
                    # อัปเดตข้อมูลเข้า DataFrame
                    data.at[selected_index, "Supplier Detail"] = supplier_val
                    data.at[selected_index, "Price"] = price_val
                    data.at[selected_index, "Attachment Link"] = final_link
                    data.at[selected_index, "Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    conn.update(worksheet="Sheet1", data=data)
                    st.success("💾 อัปเดตข้อมูลราคาและหลักฐานแนบเรียบร้อยแล้ว!")
                    st.rerun()
    else:
        st.warning("⚠️ ไม่พบข้อมูลโครงสร้างตารางหลักในระบบ")

# ====================================================================
# เมนูที่ 3: หน้าสำหรับเรียกดูข้อมูลและแสดงลิงก์ไฟล์แนบ
# ====================================================================
elif choice == "เรียกดูข้อมูลทั้งหมด":
    st.markdown("### 📊 คลังฐานข้อมูลวัสดุทั้งหมด")
    data = conn.read(worksheet="Sheet1", ttl=0)
    
    if not data.empty and "Project" in data.columns:
        project_filter = st.multiselect("กรองดูเฉพาะโครงการที่ต้องการ", options=data["Project"].unique())
        if project_filter:
            data = data[data["Project"].isin(project_filter)]
        
        # แสดงตารางหลัก
        st.dataframe(data, use_container_width=True)
        
        # 💡 ฟีเจอร์พิเศษ: ถ้าแถวไหนมีลิงก์เชื่อมโยงไฟล์ ให้ทำปุ่มกดเปิดดูแยกต่างหากด้านล่างตาราง
        st.markdown("---")
        st.markdown("🔗 **คลิกเปิดดูไฟล์แนบของรายการที่ต้องการ:**")
        
        # กรองเอาเฉพาะแถวที่มีลิงก์จริงๆ (ไม่เป็นเครื่องหมาย -)
        valid_links = data[data["Attachment Link"].str.contains("http", na=False)]
        
        if not valid_links.empty:
            for idx, row in valid_links.iterrows():
                # สร้างปุ่มเปิดลิงก์สำหรับแต่ละโปรเจกต์
                st.link_button(f"🔗 เปิดไฟล์แนบของ [{row['Project']}] - {row['Material Request'][:20]}...", row["Attachment Link"])
        else:
            st.text("ไม่มีไฟล์แนบที่ระบุเป็นลิงก์ URL ในระบบขณะนี้")
            
        if "Price" in data.columns:
            total_price = pd.to_numeric(data["Price"]).sum()
            st.metric("มูลค่าราคารวมในระบบขณะนี้", f"{total_price:,.2f} บาท")
