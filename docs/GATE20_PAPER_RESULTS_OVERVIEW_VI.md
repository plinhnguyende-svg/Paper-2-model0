# Paper 2 — Tổng hợp kết quả sau Gate 20

## 1. Nghiên cứu đang giải thích điều gì?

Paper phân tích cách quy tắc smart contracts ảnh hưởng đến giao dịch tín chỉ,
phân bổ giá trị và khả năng truyền lợi ích về biochar producers. CHAR là bối cảnh
thể chế và kiểm chứng cơ chế. Kết quả lý thuyết phải được phân biệt với bằng chứng
về giao dịch thực tế và tác động sản xuất ngoài đời.

Chuỗi giải thích hiện tại là: quy tắc phí và thực thi -> quyết định credit holder/
intermediary -> lợi ích monetization -> hợp đồng pass-through -> quyết định sản xuất.
Không đồng nhất fee recipient, depositor, CORC owner và producer.

## 2. Các nhóm kết quả đã có

| Nhóm | Kết quả | Phạm vi có thể khẳng định |
|---|---|---|
| Cơ chế tính/phân bổ phí | Đã audit source và các checkpoint calculator; deposit minting khác redemption transfers | Có cơ chế lập trình; chưa chứng minh royalties đến producer |
| Participation | Có ngưỡng payoff cho deposit và redemption, tính outside option và gas | Quyết định cá nhân khi giá và lot/state được cho trước |
| maxFee | Có optimal acceptance threshold và so sánh submission với abstention | Exogenous fee distribution; không luôn có cap duy nhất |
| Inventory | Có accounting identities của HHI và project-level inventory | Không phải bằng chứng fees gây diversification hoặc tăng removal |
| Boundary và execution | Source-default có nhánh single-project riêng; real limit khác EVM dust behavior; H0 dynamic domain khác S0 | Phân biệt real formula, source EVM, deployed calculator và whole-pool transaction |
| Thiết kế phí | Continuity không đảm bảo monotonic incentives; đã có clipping/extension và finite policy searches | Không phải functional optimum hoặc empirical performance improvement |
| Producer cố định premium | Có nghiệm toàn cục với cash constraint và điều kiện pass-through | Chỉ khi premium trên mỗi credit không bị own output làm thay đổi |
| Producer nội sinh lượng | Đã giải bài toán ngoài/pool bằng hai nhánh, chỉ ra global tie và khả năng higher profit/lower output | Gate 19 yêu cầu all-output single-channel routing |
| Partial pooling | Output không thấp hơn outside benchmark; premium có thể bão hòa | Gate 20 cho phép bán phần dư ngoài với điều kiện không đổi |
| Tách lô | Tổng phí số thực cùng-project tự triệt tiêu theo potential; thêm gas làm self-splitting kém hơn | Không có third-party flows, rule changes, thresholds hoặc EVM rounding |
| Identification | Fee shares không nhận diện được contractual beta hoặc producer financing | Cần bằng chứng ví, quyền sở hữu và hợp đồng thương mại riêng |

## 3. Kết quả nào quan trọng nhất về mặt kinh tế?

### A. Smart-contract rules tác động đến participation bằng net value

Depositor không chỉ nhìn fee rate. Họ so sánh giá trị CHAR nhận được sau phí và gas
với giá trị giữ/bán credits ngoài pool. Nếu người giao dịch cũng nhận lại một phần
phí, private net cost khác gross fee. Thay đổi shares giữa những người không tham
gia quyết định, trong baseline giá ngoại sinh, chỉ phân phối lại giá trị và không
tự động thay đổi participation.

### B. Tính liên tục và tính khuyến khích là hai yêu cầu khác nhau

Gate 11 chứng minh anchored smoothing có thể làm phí liên tục tại ranh giới nhưng
không giữ được deposit/redemption monotonicity mong muốn. Vì vậy thiết kế không
thể chỉ tối ưu một tiêu chí kỹ thuật. Tuy nhiên, clipping/extension vẫn là đề xuất
được kiểm tra trong mô hình số thực, chưa phải policy deployed hoặc một cơ chế tối ưu.

### C. Thực thi giao dịch là một quyết định kinh tế

Cap chặt có thể làm mất giao dịch có lợi; cap rộng có thể chấp nhận phí cao quá mức.
Threshold utility-consistent không cần đạt completion cao nhất. Kết quả này có điều
kiện về distribution, gas, other checks và ownership; không phải kết quả cân bằng
strategic transaction ordering.

### D. Lợi ích giao dịch không tự động thành vốn upstream

Beta là quyền hưởng phần premium theo hợp đồng, khác cấu hình fee recipients. Nếu
beta=0 và các primitives khác cố định, producer output không đổi dù intermediary
vẫn có thể hưởng lợi và giao dịch. Nếu vốn trước sản xuất đã binding, thu nhập về
sau không tự làm tăng cash khả thi trước sản xuất.

### E. Kết luận sản lượng phụ thuộc marketing flexibility

Gate 19 làm premium phụ thuộc sản lượng, với toàn bộ lot phải đi qua một kênh.
Chi phí biên pooling có thể tăng đủ nhanh để producer muốn sản xuất ít hơn nhưng
nhận lợi nhuận cao hơn. Gate 20 cho phép chọn lot pooling nhỏ hơn tổng sản lượng:
intermediary giữ lot có lợi và bán phần dư ngoài. Vì tập lựa chọn pooling không
thu hẹp khi sản lượng tăng, premium tối ưu không giảm theo sản lượng; từ đó chứng
minh output tối ưu không thể thấp hơn outside-only benchmark.

Do đó không được dùng Gate 19 làm theorem tổng quát "pooling giảm sản lượng".
Kết quả được giữ là một contrast có điều kiện để chỉ rõ tác động của contractual
restrictions/venue allocation. Đây là điều chỉnh kết luận sau robustness, không
phải một mâu thuẫn giữa hai phép tính cùng mô hình.

### F. Producer có thể nhận thêm giá trị nhưng không mở rộng sản xuất

Ngay cả khi beta>0 và vốn không binding, nếu lot pooling tối ưu đã đạt bão hòa ở
sản lượng baseline, phần sản xuất thêm chỉ bán ngoài. Producer nhận khoản premium
mà không có động cơ tăng output. Pooling saturation và cash constraint là hai
nguyên nhân khác nhau cho cùng hiện tượng không tăng sản lượng.

## 4. Minh họa cùng một bộ tham số giả định

| Chỉ tiêu | Outside-only | All-output Gate 19 | Partial Gate 20 |
|---|---:|---:|---:|
| Sản lượng | 35.000000 | 30.960317 | 35.000000 |
| Credits vào pool | 0 | 30.960317 | 22.049335 |
| Credits bán ngoài | 35.000000 | 0 | 12.950665 |
| Lợi nhuận producer | 6.125000 | 6.421936 | 6.663262 |

Các con số dùng source formula với historical-parameter substitution, không phải
đo lường production hoặc deployed transaction. Chúng minh họa một cơ chế dưới các
giả định hợp đồng đã nêu, không chứng minh causal effect trong ngành biochar.

## 5. Phần đã kiểm chứng và phần chưa được phép kết luận

Original Gates 9–13 main numerical workflows đã tái lập; 27 CSV thực sự được tái
tạo khớp bản lưu trong sai số 1e-10. GitHub replay đối chiếu 20 summary tables.
Gate 11 có 6,720 lượt simulation, các nghiệm extension đồng hạng; khoảng tin cậy
mô phỏng cho cải thiện volume bao gồm zero. Gate 18/19/20 có các tests mới riêng.
Tính tái lập không nâng synthetic results thành empirical evidence.

Source EVM và deployed calculator fork đã có PASS tại các checkpoint được nêu.
Exact source-bytecode matching và whole-pool transaction reconciliation vẫn chưa
hoàn tất. Thu thập eth_getLogs ở các runs gần nhất bị lỗi; không có candidate
không đồng nghĩa không có hoạt động. Recipient-to-producer attribution, commercial
beta, realized producer financing và additional physical removal chưa được xác minh.

## 6. Đánh giá độ hoàn thiện của paper

Đã có một hệ thống economic mechanism analysis với institutional audit, propositions,
continuous quantity/channel optimization và reproducible computational experiments.
Đã có nhiều kết quả giúp loại bỏ claims sai, cùng một số trade-offs cần phát triển.

Chưa có một flagship optimal mechanism theorem trên cả fee-rule space, chưa có
governance equilibrium hoặc endogenous token-market equilibrium, chưa có identification
về tác động thực tế. Literature novelty audit chưa đóng. Chỉ gọi là "mechanism design"
ở phần nào thực sự có designer objective, admissible choices và response/constraints;
không xem các individual optimizations tự động là optimal mechanism.

Định vị contribution hiện tại nên là một đề xuất có điều kiện: economic design of
programmable market rules and contractual transmission trong environmental supply
chains. Không cần gắn kết quả với blockchain superiority, nhưng phải giải thích
phần insight nào xuất phát từ contract rule cụ thể và phần nào là nguyên lý routing/
revenue-sharing chung. Output-floor theorem của Gate 20 thuộc nhóm nguyên lý kinh
tế chung, được dùng để kiểm tra chặt chẽ smart-contract application.

## 7. Bước nghiên cứu kế tiếp

Đưa response partial-pooling đã giải vào designer problem: ai chọn fee rule, mục
tiêu kinh tế nào được tối ưu, ràng buộc nào có nền tảng thể chế, và thiết kế tốt hơn
benchmark ở những điều kiện nào. Giữ endogenous pricing và governance game ngoài
baseline cho đến khi cần thiết. Tiếp tục transaction matching như evidence workstream
riêng, không dùng lỗi RPC làm lý do giữ một kết quả lý thuyết không robust.

## Ghi chú incentive tại endpoint

Khi beta<1, intermediary còn hưởng một phần premium nên tối ưu margin dẫn đến
lot pooling tối ưu. Khi beta=1, cần mandate theo hợp đồng hoặc tie-break ưu tiên
producer vì intermediary không còn hưởng phần tăng thêm. Các phép tính tại beta=1
dùng quy ước này; ví dụ chính beta=.25 không cần dựa vào endpoint đó.
